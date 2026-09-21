# Testing API Keys

Setup a virtual environment, install the dependencies, and activate the virtual environment using [Make](./dev_guide.md#using-the-makefile)

## Validation with `check-llm-keys`

Run `neuro-san-studio check-llm-keys` to validate your API keys using a three-tier system. You can
specify the tier level with `--tier`:

- `neuro-san-studio check-llm-keys` or `neuro-san-studio check-llm-keys --tier 3` — Run all three tiers (default)
- `neuro-san-studio check-llm-keys --tier 1` — Run only Tier 1
- `neuro-san-studio check-llm-keys --tier 2` — Run Tiers 1 and 2

See [cli/check_llm_keys.md](./cli/check_llm_keys.md) for the full command reference, including exit-code semantics.

### Tier 1: Placeholder Detection

Detects common placeholder values that indicate unconfigured keys.

**Detected patterns:** `YOUR_`, `REPLACE`, `CHANGEME`, `INSERT`, `TODO`, `<`, `>`, `xxx`, `...`

**Examples:**
| Value | Result |
|-------|--------|
| `YOUR_OPENAI_API_KEY` | ⚠️ Placeholder detected |
| `<insert-key-here>` | ⚠️ Placeholder detected |
| `sk-proj-abc123...` | ✓ Passes to Tier 2 |

### Tier 2: Format Validation

Validates that API keys match expected patterns for each provider.

**Format rules:**
| Provider | Expected Format |
|----------|-----------------|
| OpenAI | Starts with `sk-`, at least 20 characters |
| Anthropic | Starts with `sk-ant-`, at least 20 characters |
| Google | At least 20 characters |
| AWS Access Key | Starts with `AKIA`, exactly 20 characters |
| AWS Secret Key | Exactly 40 characters |
| Azure OpenAI | At least 20 characters |

**Examples:**
| Value | Result |
|-------|--------|
| `sk-proj-abc123def456...` | ✓ Valid OpenAI format |
| `invalid-key` | ❌ Invalid format |
| `sk-ant-api03-xyz...` | ✓ Valid Anthropic format |

### Tier 3: Live Validation

Makes actual API calls to verify keys are valid and have access.
This tier runs by default, or when `--tier 3` is explicitly passed.

**Currently supported providers for live validation:**

- ✅ OpenAI (calls `/v1/models`)
- ✅ Anthropic (calls `/v1/messages/count_tokens`)
- ✅ Google (calls Gemini models list)

**Not yet supported:** AWS, Azure OpenAI (these only get Tier 1 & 2 validation)

### Example Output

```text
======================================================================
Environment Variable Validation Results
======================================================================

[VALID]
  OPENAI_API_KEY: sk-pr...xY9z - API key verified
  GOOGLE_API_KEY: AIza...cntU - API key verified
  ANTHROPIC_API_KEY: sk-an...swAA - API key verified

[WARNING]
  - AWS_ACCESS_KEY_ID: not set - Configure in .env file
  - AWS_SECRET_ACCESS_KEY: not set - Configure in .env file
  - AZURE_OPENAI_API_KEY: not set - Configure in .env file
  - AZURE_OPENAI_ENDPOINT: not set - Configure in .env file

======================================================================
Summary: 3/7 valid, 4 warnings, 0 errors
======================================================================
```

> **Source Code:** The validation logic lives in
> [`neuro_san_studio/commands/check_llm_keys.py`](../neuro_san_studio/commands/check_llm_keys.py).
> You can inspect or extend this file to add support for additional providers.

---

## Testing Keys via CLI

You can test individual or all API keys using the built-in `check-llm-keys` command:

```bash
# Validate all configured keys across all 3 tiers (format & live ping)
ns check-llm-keys --tier 3

# Validate only format & placeholders
ns check-llm-keys --tier 2
```

### Environment Variables Quick Reference

Configure your keys in your `.env` file:

```bash
# OpenAI
OPENAI_API_KEY="sk-proj-..."

# Anthropic
ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
GOOGLE_API_KEY="AIzaSy..."

# Azure OpenAI
AZURE_OPENAI_API_KEY="your-key"
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"
```
