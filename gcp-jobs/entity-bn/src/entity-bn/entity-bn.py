import os
import shutil
import sys
import pathlib
from datetime import UTC, datetime

import papermill as pm
from dotenv import find_dotenv, load_dotenv

from structured_logging import StructuredLogging

# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())

logging = StructuredLogging().get_logger()

if __name__ == "__main__":
    start_time = datetime.now(UTC)

    data_dir = os.path.join(os.getcwd(), r"data/")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    path = pathlib.Path(__file__).parent.resolve()
    file = os.path.join(path, "tracker-errors.ipynb")
    pm.execute_notebook(file, data_dir+"temp.ipynb", parameters=None)

    shutil.rmtree(data_dir)
    end_time = datetime.now(UTC)
    logging.info("job - jupyter notebook report completed in: %s", end_time - start_time)
    sys.exit()
