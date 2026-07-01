# How to publish NotifyFork to PyPI

## First time setup

```bash
pip install hatch twine

# Create account at https://pypi.org and https://test.pypi.org
# Generate API tokens in your account settings
```

## Test on TestPyPI first (always)

```bash
# Build
hatch build

# Upload to TestPyPI
twine upload --repository testpypi dist/*
# enter: __token__ as username, your TestPyPI token as password

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ notifyfork

# Test it works, then publish to real PyPI
```

## Publish to PyPI

```bash
twine upload dist/*
# enter: __token__ as username, your PyPI token as password
```

## Release a new version

1. Update `version` in `pyproject.toml`
2. Add entry to `CHANGELOG.md`
3. Commit and tag: `git tag v0.2.0 && git push --tags`
4. Build and upload: `hatch build && twine upload dist/*`

## pip install after publishing

```bash
# Core only
pip install notifyfork

# With Twilio
pip install "notifyfork[twilio]"

# With Firebase
pip install "notifyfork[firebase]"

# Everything
pip install "notifyfork[all]"
```
