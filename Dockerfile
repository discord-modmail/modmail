FROM python:3.9-slim

# Set pip to have cleaner logs and no saved cache
ENV PIP_NO_CACHE_DIR=false \
    POETRY_VIRTUALENVS_CREATE=false

# Install poetry
RUN pip install -U poetry==1.1.11

# See https://github.com/python-poetry/poetry/issues/3336
RUN poetry config experimental.new-installer false

# Create the working directory
WORKDIR /modmail

# export a dependency file
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry export --without-hashes > generated_requirements.txt

# Install project dependencies
RUN pip install -r generated_requirements.txt

# Copy the source code in next to last to optimize rebuilding the image
COPY . .

# install the package using pep 517 but do not include the dependencies as they've already been installed
RUN pip install . --no-deps


CMD ["python", "-m", "modmail"]
