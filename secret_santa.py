import argparse
import json
import os
import smtplib
from collections import defaultdict
from datetime import datetime
from email.mime.text import MIMEText

import numpy as np
from scipy.optimize import linear_sum_assignment
from dotenv import load_dotenv
from jinja2 import Template

DEFAULT_CONFIG_FILE = "config.json"
DEFAULT_HISTORY_DIR = "history"

# Default email templates (Jinja2 syntax)
DEFAULT_EMAIL_SUBJECT = "🎅 Secret Santa {{ year }}!"
DEFAULT_EMAIL_BODY = """Hi {{ giver_names }},

You are the Secret Santa for: {{ receiver_names }}!

Merry Christmas! 🎄"""

# ------------------ Load & Save History ------------------
def load_history(history_dir: str):
    """Load all yearly assignment files and normalize giver/receiver to tuples."""
    history = {"assignments": []}
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
        return history

    for filename in os.listdir(history_dir):
        if filename.endswith(".json"):
            with open(os.path.join(history_dir, filename), "r") as f:
                data = json.load(f)

                # Normalize pairs to tuples
                normalized_pairs = []
                for g, r in data["pairs"]:
                    normalized_pairs.append((g, r))

                history["assignments"].append({
                    "year": data["year"],
                    "pairs": normalized_pairs
                })
    return history

def history_file_for_year(history_dir, year):
    return os.path.join(history_dir, f"{year}.json")

def save_history(history_dir, year, pairs):
    """Save group assignments flattened into individual-to-individual pairs."""
    filepath = history_file_for_year(history_dir, year)
    flat_pairs = []
    for giver_group, receiver_group in pairs:
        for g in giver_group:
            for r in receiver_group:
                flat_pairs.append((g, r))
    with open(filepath, "w") as f:
        json.dump({"year": year, "pairs": flat_pairs}, f, indent=2)

# ------------------ Assignment Algorithm ------------------
def build_weighted_candidates(current_year, members, history):
    """
    Build candidate list with weights.
    Weight = 0 if never assigned.
    Otherwise, penalize for assignments by recency and amount.
    """
    past_assignments_to_year = defaultdict(list)
    min_year = min(record["year"] for record in history["assignments"])
    for record in history["assignments"]:
        y = record["year"]
        for giver, receiver in record["pairs"]:  # both tuples
            past_assignments_to_year[(giver, receiver)].append(y)

    candidates = {}
    for giver in members:
        giver_group = tuple(sorted(giver["group"]))
        excluded_people = set(giver.get("exclude", []))
        candidates[giver_group] = []

        for potential_receiver in members:
            potential_receiver_group = tuple(sorted(potential_receiver["group"]))
            if giver_group == potential_receiver_group:
                # Skip self assignment
                continue
            if any(person in excluded_people for person in potential_receiver_group):
                # Skip excluded people
                continue

            years_list = []
            for g in giver_group:
                for r in potential_receiver_group:
                    years_list.extend(past_assignments_to_year.get((g, r,), []))

            weight = 0
            for y in years_list:
                # Weight is 1 for the oldest assignment, and higher if more recent
                # E.g. if Secret Santa started in 2020 and this candidate was assigned in 2021, weight is 2
                weight += y - min_year + 1
            candidates[giver_group].append((potential_receiver_group, weight))

    return candidates

def find_assignments(members, candidates):
    """Use Hungarian algorithm to minimize total weight."""
    givers = [tuple(sorted(m["group"])) for m in members]
    receivers = givers[:]
    n = len(givers)

    impossible_assignment_weight = 1e6
    cost_matrix = np.full((n, n), impossible_assignment_weight)

    for i, giver in enumerate(givers):
        for receiver, weight in candidates[giver]:
            j = receivers.index(receiver)
            cost_matrix[i, j] = weight

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    pairs = []
    for i, j in zip(row_ind, col_ind):
        if cost_matrix[i, j] == impossible_assignment_weight:
            return None
        pairs.append((givers[i], receivers[j]))
    return pairs

# ------------------ Template Rendering ------------------
def render_template(template_string, variables):
    """Render Jinja2 template with variables."""
    template = Template(template_string)
    return template.render(**variables)

# ------------------ Email Handling ------------------
def send_email(smtp_server, smtp_port, smtp_user, smtp_password, to_email, subject, body):
    msg = MIMEText(body)
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

# ------------------ Main ------------------
def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print assignments instead of emailing")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG_FILE, help="Path to config file")
    parser.add_argument("--history-dir", type=str, default=DEFAULT_HISTORY_DIR, help="Path to history directory")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Year to assign")
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print(f"Missing config file: {args.config}")
        return
    with open(args.config, "r") as f:
        config_data = json.load(f)
    
    members = config_data.get("members", [])
    if "email_templates" in config_data:
        email_subject = config_data["email_templates"].get("subject", DEFAULT_EMAIL_SUBJECT)
        email_body = config_data["email_templates"].get("body", DEFAULT_EMAIL_BODY)
    else:
        email_subject = DEFAULT_EMAIL_SUBJECT
        email_body = DEFAULT_EMAIL_BODY

    history = load_history(args.history_dir)

    year = args.year
    year_history_path = history_file_for_year(args.history_dir, year)
    if os.path.exists(year_history_path):
        print(f"Assignments for year {year} already exist! Delete {year_history_path} to re-run or change year via --year.")
        return

    candidates = build_weighted_candidates(year, members, history)
    assignments = find_assignments(members, candidates)

    if not assignments:
        print("No valid assignment found! Try adjusting constraints.")
        return

    save_history(args.history_dir, year, assignments)

    # Print compromises
    compromises = []
    for giver_group, receiver_group in assignments:
        for g in giver_group:
            for r in receiver_group:
                for record in history["assignments"]:
                    if (g, r,) in record["pairs"]:
                        compromises.append(f"Compromise: {g} already gave to {r} in {record['year']}")
    if len(compromises) > 0:
        compromises_filename = os.path.join(args.history_dir, f"{year}_compromises.txt")
        with open(compromises_filename, "w") as f:
            f.write("\n".join(compromises) + "\n")
        print(f"Total compromises: {len(compromises)} (details in {compromises_filename})")
    else:
        print("No compromises made, everyone is a new match!")

    # Notify everyone
    for giver, receiver in assignments:
        giver_member = next(m for m in members if tuple(sorted(m["group"])) == giver)
        to_email = giver_member["email"]
        
        template_vars = {
            'year': year,
            'giver_names': ', '.join(giver),
            'receiver_names': ', '.join(receiver)
        }
        
        # Render templates
        subject = render_template(email_subject, template_vars)
        body = render_template(email_body, template_vars)

        if args.dry_run:
            print(f"[DRY RUN] Email to {to_email}:")
            print(f"Subject: {subject}")
            print(f"Body:\n{body}\n")
        else:
            # Load environment variables from .env file
            load_dotenv()
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            if not smtp_host or not smtp_port or not smtp_user or not smtp_password:
                print("Error: SMTP settings not found in .env file")
                return
            
            send_email(smtp_host, smtp_port, smtp_user, smtp_password, to_email, subject, body)
            print(f"Sent to {to_email}")

if __name__ == "__main__":
    main()
