FROM python:3.9-slim

# Set pip to have cleaner logs and no saved cache
# Set poetry to not make virtualenvs
# set pipx to use the same folder that pip puts scripts in
ENV PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_CREATE=false \
    PIPX_BIN_DIR=/usr/local/bin


# Install poetry with pipx
RUN pip install -U pipx==0.16.4
RUN pipx install poetry==1.1.7

# See https://github.com/python-poetry/poetry/issues/3336
RUN poetry config experimental.new-installer false

# Create the working directory
WORKDIR /modmail

# Copy the source code in last to optimize rebuilding the image
COPY . .

# Install project dependencies
RUN poetry install --no-dev

CMD ["python", "-m", "modmail"]
