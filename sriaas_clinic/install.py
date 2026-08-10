# apps/sriaas_clinic/sriaas_clinic/install.py
from .setup.roles import ensure_required_roles
from .setup.runner import setup_all


def run_setup():
    ensure_required_roles()
    setup_all()


def after_install():
    run_setup()


def after_migrate():
    run_setup()
