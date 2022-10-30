# Java Hooks for pre-commit

This repository contains some pre-commit hooks that are useful for working with
Java code.

## Hooks

- `check-java-package-statements` - Checks if a package statement is present
  and matches the filesystem path
- `unused-java-imports` - Removes unused imports from Java source files

## Usage

Add the following lines to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/Holzhaus/pre-commit-hooks-java
  rev: ""
  hooks:
    - id: check-java-package-statements
    - id: unused-java-imports
```

Either specify a specific hook version in the `rev` field directly, or run the
this command to automatically fill in the latest version:

```shell-session
$ pre-commit autoupdate --repo "https://github.com/Holzhaus/pre-commit-hooks-java"
Updating https://github.com/Holzhaus/pre-commit-hooks-java ... updating  -> <latest-version>.
```
