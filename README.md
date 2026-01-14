# Canonical CLA

Canonical Contribution Licence Agreement (CLA) Service.

## Requirements

- Python 3.12+
- Poetry: [Installation instructions](https://python-poetry.org/docs/#installation)

## Installation

```
poetry install
poetry run setup
```

The `setup` command installs pre-commit hooks that will automatically format your code before each commit.

## Usage

- Run development server:

  ```
  poetry run dev
  ```

- Format code:

  ```
  poetry run format
  ```

- Run unit tests:

  ```
  poetry run test
  ```

- Run tests with coverage:

  ```
  poetry run test --coverage
  ```

- Run migrations:
  ```
  poetry run migrate --apply
  ```

## Documentation

For more detailed information, visit the [official documentation](https://cla.canonical.com/docs).

## Deployment

This project has a Charmed operator that can be found at: https://github.copm/canonical/charmed-canonical-cla.

## License

This project is licensed under the Apache 2.0 License.
