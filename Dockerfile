FROM python:3.9-slim

# Set pip to have cleaner logs and no saved cache
# Set poetry to not make virtualenvs
# set pipx to use the same folder that pip puts scripts in
ENV PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_INSTALLER_PARALLEL=false \
    PIPX_BIN_DIR=/usr/local/bin

# install poetry
# this is pinned because sometimes versions have bugs, and this version is reliable enough to use
RUN pip install poetry==1.1.7

# See https://github.com/python-poetry/poetry/issues/3336
RUN poetry config experimental.new-installer false

# Create the working directory
WORKDIR /modmail

# copy the required files to install the dependencies.
COPY ./pyproject.toml .
COPY ./poetry.lock .


# Install project dependencies
RUN poetry install --no-dev --no-root

# Copy the source code in last to optimize rebuilding the image
COPY . .

# install the package itself.
# this is required for importlib.metadata to work
RUN poetry install --no-dev

CMD ["poetry","run","python", "-m", "modmail"]
