FROM python:3.9-slim

# Set pip to have cleaner logs and no saved cache
ENV PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_CREATE=false

# HACK: Git is required to install a pinned version of discord.py master
# /var/lib/apt/lists is where `apt-get update` downloads are stored, they can be removed
# as they are recreated when package lists are updated and are redundant
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install -U poetry

# See https://github.com/python-poetry/poetry/issues/3336
RUN poetry config experimental.new-installer false

# Create the working directory
WORKDIR /modmail

# Copy the source code in last to optimize rebuilding the image
COPY . .

# Install project dependencies
RUN poetry install --no-dev

CMD ["python", "-m", "modmail"]
