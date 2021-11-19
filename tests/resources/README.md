# About
Resources for tests.

When adding a resource, it should be in the module to be tested corresponding folder.

For example, a resource for testing modmail should go in `tests/resources/modmail`.

To use a resource, there is a fixture in the module's conftest.py named `resource_path` which returns the proper pathlib.Path for the module.
