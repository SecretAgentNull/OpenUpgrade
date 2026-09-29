# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Odoo 20.0 deletes the ``ir.rule`` and ``ir.model.access`` models and replaces
both by a single ``ir.access`` model, fed by the new ``security/ir.access.csv``
files. Odoo SA ships no database conversion for it (``odoo/addons/base`` has no
``migrations`` folder and ``odoo/upgrade_code/19.4-00-ir-access.py`` only
rewrites the *source* files of addons), so OpenUpgrade has to prepare the
database here.

This runs in the pre-migration of ``base`` because that is the first node of the
module graph: every other module loads its ``security/ir.access.csv`` afterwards.

The same script also repairs the re-keyed ``res.country.state`` external ids of
base's own data file, which would otherwise abort the upgrade before any other
module gets a chance to load, and re-homes the external ids of the addons that
20.0 merged into others.
"""

import csv
import os

from openupgradelib import openupgrade

from odoo.modules import get_module_path

# pylint: disable=odoo-addons-relative-import
from odoo.addons.openupgrade_scripts.apriori import merged_modules, renamed_modules

# models that exist in 19.0 but not in 20.0
REMOVED_MODELS = ("ir.rule", "ir.model.access")

# ir.model.data names of the metadata records describing those two models
REMOVED_MODEL_XMLIDS = ("model_ir_rule", "model_ir_model_access")

LEGACY_PREFIX = "openupgrade_legacy_"

# base data file whose record ids 20.0 re-keyed
STATE_CSV = ("data", "res.country.state.csv")


def apply_module_moves(env):
    """20.0 folds hr_org_chart, hr_homeworking, hr_homeworking_calendar and
    hr_hourly_cost into other addons.

    Their records keep the external id they had, so the data file of the
    successor addon reads them as new records and the insert stops on a unique
    constraint of the model (ir_act_window_path_unique, ...). Moving the
    ir.model.data rows to the successor deletes the module row and renames the
    dependency entries, so the whole graph stays consistent. Colliding names get
    an ``_openupgrade_<id>`` suffix and noupdate=FALSE, which lets Odoo's own
    cleanup remove the obsolete record.
    """
    openupgrade.update_module_names(
        env.cr, renamed_modules.items(), environment_namespec=True
    )
    openupgrade.update_module_names(
        env.cr, merged_modules.items(), merge_modules=True, environment_namespec=True
    )


def reconcile_country_state_xmlids(env):
    """20.0 renamed the external ids of many states: they follow the state code
    now, so ``state_in_or`` became ``state_in_od`` (Odisha, code OD) and the
    whole of ``state_sa_1``..``state_sa_38`` became ``state_sa_01``....

    A csv import matches on the id column only, so a renamed line is read as a
    brand new state and its insert stops on
    ``res_country_state_name_code_uniq`` (UNIQUE (country_id, code)), which
    aborts the loading of base. Pair the file up with the database by
    (country, code) and move the stale ids over: the states that customers have
    picked on their partners are then updated instead of duplicated.
    """
    module_path = get_module_path("base", display_warning=False)
    if not module_path:
        return
    with open(
        os.path.join(module_path, *STATE_CSV), newline="", encoding="utf-8"
    ) as handle:
        file_rows = [
            (row["id"], row["country_id:id"], row["code"])
            for row in csv.DictReader(handle)
            if row.get("id")
        ]
    file_ids = {name for name, country, code in file_rows}
    by_pair = {(country, code): name for name, country, code in file_rows}
    openupgrade.logged_query(
        env.cr,
        """
        SELECT state_xid.name, country_xid.name, state.code
        FROM ir_model_data state_xid
        JOIN res_country_state state ON state.id = state_xid.res_id
        JOIN ir_model_data country_xid
            ON country_xid.res_id = state.country_id
            AND country_xid.model = 'res.country'
            AND country_xid.module = 'base'
        WHERE state_xid.model = 'res.country.state' AND state_xid.module = 'base'
        """,
    )
    stored = env.cr.fetchall()
    known_ids = {name for name, country, code in stored}
    renames = [
        (f"base.{name}", f"base.{renamed}")
        for name, country, code in stored
        if name not in file_ids
        # only take an id that no other record of the database owns
        for renamed in [by_pair.get((country, code))]
        if renamed and renamed not in known_ids
    ]
    if renames:
        openupgrade.rename_xmlids(env.cr, renames)
        openupgrade.message(
            env.cr,
            "base",
            "ir.model.data",
            "name",
            "Renamed %d res.country.state external ids to the names 20.0 uses in "
            "base/data/res.country.state.csv, so that the file updates the "
            "existing states instead of creating duplicates: %s.",
            len(renames),
            ", ".join(f"{old} -> {new}" for old, new in renames[:10]),
        )


def free_reused_xmlids(env):
    """20.0 reuses the external ids of 19.0 access rights and record rules for its
    ``ir.access`` records (91 of the 141 rows of base's security/ir.access.csv
    carry the name of an existing ``ir.model.access`` row, e.g.
    ``access_decimal_precision_config``).

    ``ir.model.data`` is unique on ``(module, name)`` only, and
    ``BaseModel._load_records`` raises a ValidationError when the existing row
    points to another model, so the upgrade aborts on the first security file
    unless the stale rows are moved out of the way. They are renamed instead of
    deleted: the old record still has no model in the registry, but the row keeps
    telling us which accesses were standard module data and which ones the
    customer created by hand.
    """
    openupgrade.logged_query(
        env.cr,
        f"""
        UPDATE ir_model_data imd
        SET name = '{LEGACY_PREFIX}' || imd.name
        WHERE imd.model IN %s
            AND imd.name NOT LIKE %s
            AND NOT EXISTS (
                SELECT 1
                FROM ir_model_data other
                WHERE other.module = imd.module
                    AND other.name = '{LEGACY_PREFIX}' || imd.name
            )
        """,
        (REMOVED_MODELS, LEGACY_PREFIX + "%"),
    )


def protect_removed_model_metadata(env):
    """Keep the ``ir.model`` / ``ir.model.fields`` rows of the removed models.

    ``ir.model.data._process_end`` deletes every non noupdate record of an
    upgraded module that 20.0 did not reload, and ``ir.model`` *is* still a model
    of the registry, so ``base.model_ir_rule`` and friends would be deleted. The
    ``model_id`` fields of both legacy tables are declared ``ondelete='cascade'``,
    which means dropping those metadata rows would cascade straight into the
    customer's own record rules and access rights. Removing only the external ids
    makes the metadata invisible to ``_process_end`` while keeping the data.
    """
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM ir_model_data
        WHERE (model = 'ir.model' AND name = ANY(%s))
            OR (
                model = 'ir.model.fields'
                AND (name LIKE ANY(%s) OR name LIKE ANY(%s))
            )
        """,
        (
            list(REMOVED_MODEL_XMLIDS),
            ["field\\_ir\\_rule\\_\\_%"],
            ["field\\_ir\\_model\\_access\\_\\_%"],
        ),
    )


def warn_about_legacy_access_records(env):
    openupgrade.logged_query(
        env.cr,
        """
        SELECT
            (SELECT count(*) FROM ir_rule),
            (SELECT count(*) FROM ir_model_access)
        """,
    )
    n_rules, n_access = env.cr.fetchone()
    openupgrade.message(
        env.cr,
        "base",
        False,
        False,
        f"The tables ir_rule ({n_rules} rows) and ir_model_access ({n_access} rows) "
        "of 19.0 are "
        "kept as they are, but 20.0 ignores them: access rights and record rules "
        "are now read from the new ir_access table, which is filled from the "
        "security/ir.access.csv files of the modules. Records that were created "
        "by modules have kept a copy of their external id (prefixed with "
        f"'{LEGACY_PREFIX}'), so everything in those two tables that has no such copy "
        "was created by a user and is now lost from the point of view of 20.0. "
        "Recreate them, or convert them into ir_access rows "
        "(operation: r=read, u=write, c=create, d=unlink; a rule with per-mode "
        "domains needs one ir_access row per mode).",
    )


@openupgrade.migrate()
def migrate(env, version):
    apply_module_moves(env)
    reconcile_country_state_xmlids(env)
    free_reused_xmlids(env)
    protect_removed_model_metadata(env)
    warn_about_legacy_access_records(env)
