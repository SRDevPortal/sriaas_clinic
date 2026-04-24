__version__ = "0.0.1"

# Load S3 File monkey-patches early so they apply during File.save()/validate(),
# not only after File doc events import the hook module.
from sriaas_clinic.api.s3 import file_hooks as _s3_file_hooks  # noqa: F401
