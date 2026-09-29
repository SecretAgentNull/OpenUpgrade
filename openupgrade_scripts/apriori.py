# Copyright Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Encode any known changes to the database here
to help the matching process
"""

# Renamed modules is a mapping from old module name to new module name
renamed_modules = {
    # odoo
    # odoo/enterprise
    # OCA/...
}

# Merged modules contain a mapping from old module names to other,
# preexisting module names
merged_modules = {
    # odoo
    "hr_homeworking": "hr",
    "hr_homeworking_calendar": "hr_calendar",
    "hr_hourly_cost": "hr",
    "hr_org_chart": "hr",
    # OCA/...
}

# only used here for upgrade_analysis
renamed_models = {
    # odoo
    "hr.contract.type": "hr.employee.type",
    # OCA/...
}

# only used here for upgrade_analysis
merged_models = {}

# Addons that 20.0 drops without a successor (account_add_gln) need no entry
# here: the framework's update_list patch keeps modules that are not on disk out
# of the auto install pass, so they simply stop being loaded.
