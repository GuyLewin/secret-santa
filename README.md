# 🎅 Secret Santa Assignment System 🎅

An intelligent Secret Santa assignment system that uses the [Hungarian algorithm](https://en.wikipedia.org/wiki/Hungarian_algorithm) to optimally distribute gift assignments while minimizing repeat pairings and respecting exclusion constraints.

## Features

- **Weighted Assignment**: Uses the [Hungarian algorithm](https://en.wikipedia.org/wiki/Hungarian_algorithm) to find the globally optimal assignment that minimizes total "cost" (based on historical repeats)
- **Historical Tracking**: Maintains a complete history of all previous Secret Santa assignments
- **Exclusion Support**: Allows participants to exclude specific people from being their Secret Santa
- **Group Support**: Handles both individual participants and couples/families as single units
- **Automatic Email Notifications**: Sends email notifications to all participants, allowing moderators to participate
- **Compromise Reporting**: Generates detailed reports of any unavoidable repeat assignments
- **Dry Run Mode**: Test assignments without sending emails

## Algorithm Details

The system uses a sophisticated weighting system to discourage repeat assignments:

1. **Historical Analysis**: Tracks all previous giver-receiver pairings across years
2. **Weight Calculation**: Each potential assignment gets a weight based on:
   - Number of times the pair has been matched before (including individuals in a giving or receiving group)
   - Recency of previous matches (more recent = higher penalty)
   - Formula: `weight = sum(y - min_year + 1)` for each previous assignment year `y`
3. **Optimal Assignment**: Uses the Hungarian algorithm to find the assignment with minimum total weight, while handling exclusions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/GuyLewin/secret-santa.git
cd secret_santa
```

2. (Optional) Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up email configuration:
```bash
cp .env.example .env
# Edit .env with your SMTP settings
```

## Configuration

### Participant Configuration

Create a JSON configuration file (e.g., `2025_config.json`) with participant information (under "members") and optional email template override (under "email_templates"):

```json
{
  "email_templates": {
    "subject": "🎅 Secret Santa {{ year }} - Your Assignment!",
    "body": "Hi {{ giver_names }},\n\nYou are the Secret Santa for: {{ receiver_names }}!\n\nMerry Christmas and happy gift hunting! 🎄\n\nLove,\nThe Secret Santa Coordinator",
  },
  "members": [
    {
      "group": ["John Doe"],
      "email": "johndoe@gmail.com",
      "exclude": ["Jane Smith", "Jannet Roe"]
    },
    {
      "group": ["Richard Roe", "Jannet Roe"],
      "email": "roefamily@yahoo.com",
      "exclude": []
    },
    {
      "group": ["Jane Smith"],
      "email": "janesmith@msn.com",
      "exclude": ["Richard Roe"]
    }
  ]
}
```

**`members` Item Fields:**
- `group`: Array of names in this participant unit (individual or couple / family)
- `email`: Email address for notifications
- `exclude`: Array of people this participant should not be assigned to. Everyone other group not mentioned here will be a candidate

**`email_templates` Fields (Optional):**
- `subject`: Custom email subject template.
- `body`: Custom email body template.

The system uses [Jinja2](https://jinja.palletsprojects.com/) for template rendering. The following variables are available for use in both templates:
- `{{ year }}`: The current year
- `{{ giver_names }}`: Comma-separated list of giver names
- `{{ receiver_names }}`: Comma-separated list of receiver names

### Email Configuration

Create a `.env` file in the project root with your SMTP settings:

```bash
cp .env.example .env
```

Then edit `.env` with your actual values, for example:

```env
# SMTP Server Settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Email Authentication
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Example SMTP Providers:**
- **Gmail**: `smtp.gmail.com:587` (you may need to use an App Password instead of your regular password: https://support.google.com/accounts/answer/185833)
- **Outlook/Hotmail**: `smtp-mail.outlook.com:587`
- **Yahoo**: `smtp.mail.yahoo.com:587`
- **Custom SMTP**: Use your provider's SMTP settings

## Usage

### Basic Usage

Run Secret Santa assignments for the current year:
```bash
python secret_santa.py --config 2025_config.json
```

### Command Line Options

- `--dry-run`: Print assignments without sending emails
- `--config CONFIG`: Path to participant configuration file (default: `config.json`)
- `--history-dir HISTORY_DIR`: Path to history directory (default: `history`)
- `--year YEAR`: Year to assign (default: current year)

### Examples

**Test assignments without sending emails:**
```bash
python secret_santa.py --config 2025_config.json --dry-run
```

**Use custom history directory:**
```bash
python secret_santa.py --config 2025_config.json --history-dir my_history
```

## Output

### Successful Assignment
The system will:
1. Generate optimal assignments using the Hungarian algorithm
2. Save assignments to `history/YEAR.json`
3. Send email notifications to all participants
4. Report any compromises (unavoidable repeat assignments)
If not running in dry-run (`--dry-run`), the assignments will not be printed, to allow the moderator to participate

### Compromise Reporting
If repeat assignments are unavoidable, the system creates a detailed report:
- File: `history/YEAR_compromises.txt`
- Lists all repeat assignments with the year they last occurred
- Prints total number of compromises made as command output (without names)

## History Management

The system automatically maintains a complete history of all assignments:
- **Automatic Loading**: Reads all `.json` files in the history directory
- **Normalized Storage**: Stores assignments as flattened giver-receiver pairs (to support different groups in different years)
- **Year-based Files**: Each year's assignments are stored separately
- **Cross-year Analysis**: Uses complete history for optimal assignment decisions

## Best Practices

1. **Backup History**: Keep backups of your history directory
2. **Update Exclusions**: Regularly review and update exclusion lists
3. **Email Security**: Keep your `.env` file secure and use app passwords for email authentication

## License

This project is open source and licensed under the MIT License (see the LICENSE file for details). You are free to use, modify, and distribute it according to the terms of the MIT License.