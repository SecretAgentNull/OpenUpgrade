Known issues / Roadmap
======================

* **Custom access rights and record rules are not converted.** 20.0 deletes
  ``ir.rule`` and ``ir.model.access`` and reads both from the new ``ir.access``
  model, which is fed by the ``security/ir.access.csv`` files of the addons. Odoo
  SA ships no database conversion (``odoo/addons/base`` has no ``migrations``
  folder and ``odoo/upgrade_code/19.4-00-ir-access.py`` only rewrites *source*
  files). ``scripts/base/20.0.1.3/pre-migration.py`` keeps the upgrade running:
  it frees the external ids the ``ir.access`` rows reuse and protects the metadata
  of the removed models from ``_process_end``, and it reports how many rows are
  left unread by 20.0. Turning the rules and access rights a customer created by
  hand into ``ir.access`` rows (one row per operation for a rule with per-mode
  domains) is still to be done.
* **No ``upgrade_analysis`` runs are attached yet.** The scripts were written
  against the 19.0 and 20.0 sources and validated by real upgrades, but the
  ``upgrade_analysis.txt`` / ``upgrade_analysis.yml`` files that an OCA pull
  request usually carries still have to be produced with
  ``oca/server-tools/upgrade_analysis``.
* **``openupgradelib.load_data()`` does not work on 20.0.** 20.0 trims
  ``odoo.tools`` down to ``convert_file`` (``from .convert import convert_file``),
  so the ``tools.convert_xml_import`` call of ``load_data`` raises
  ``AttributeError`` and every ``noupdate_changes.xml`` fails to load. The fix
  belongs in openupgradelib (import the function from ``odoo.tools.convert`` from
  20.0 on); ``openupgrade_scripts/scripts/sale/20.0.1.2/post-migration.py`` and
  ``sale_timesheet`` both need it. ``load_data`` with a csv file is broken on
  20.0 the same way and additionally passes an undefined ``pathname``.

Upgrade blockers found in modules outside the sale family
---------------------------------------------------------

The sale family cannot be upgraded on its own: it loads ``base``, ``mail``,
``account``, ``product``, ``uom`` and ``hr`` first. Testing 19.0 -> 20.0
hit the data churn below. Every one of
them aborts the loading of the module it belongs to, so the 20.0 branch needs a
script for each before a full-product upgrade passes CI.

A csv or xml import matches a record on its external id only, so a record whose
id 20.0 renamed or moved is read as a new one and its insert stops on a unique
constraint. The same is true when 20.0 keeps an external id but attaches it to
another model: the loader refuses a row that points at a record of a different
model.

+ ``base``: ``data/res.country.state.csv`` re-keys 96 of its 2131 ids to follow
  the state code (``state_in_or`` -> ``state_in_od``), which stops on
  ``res_country_state_name_code_uniq``. **Fixed here**, in
  ``scripts/base/20.0.1.3/pre-migration.py``.
+ ``hr_org_chart`` (merged into ``hr``), ``hr_homeworking`` and ``hr_hourly_cost``
  (merged into ``hr``) and ``hr_homeworking_calendar`` (merged into
  ``hr_calendar``) are installed in 19.0 and gone from the 20.0 tree. Their
  records keep the external ids of the removed addon while the successor addon
  declares the same records under its own module:
  ``ir_act_window_path_unique`` and
  ``ir_act_window_view_unique_mode_per_action``. **Fixed here**: the merges are in
  ``apriori.py:merged_modules`` and
  ``scripts/base/20.0.1.3/pre-migration.py`` re-homes the records with
  ``openupgrade.update_module_names()``. ``account_add_gln`` has no successor; it
  is covered by the ``update_list`` patch of ``openupgrade_framework``, which keeps
  addons that are not on disk out of the auto install pass.
+ ``sale``: 20.0 replaces the ir.actions.act_window of
  ``action_accrued_revenue_entry_sale_order_line`` by an ir.actions.server with
  the same external id
  (``sale/wizard/account_accrued_orders_wizard_views.xml``). **Fixed here**, in
  ``scripts/sale/20.0.1.2/pre-migration.py``.
+ ``mail``: ``data/discuss_channel_data.xml`` declares the membership of the
  Administrators channel, which 19.0 creates from Python without an external id,
  so the insert stops on ``discuss_channel_member_partner_unique``.
+ ``hr``: the model ``hr.contract.type`` became ``hr.employee.type`` and kept its
  ``contract_type_*`` external ids
  (``hr/data/hr_employee_type_data.xml``), so the load of ``hr`` dies on
  ``KeyError: 'hr.contract.type'`` inside ``ir_model_data._load_xmlid`` for the
  ``forcecreate`` record. The table has to be renamed as well, because 20.0
  derives ``hr_employee_type`` from the model name. ``hr`` is in the dependency
  closure of ``sale_timesheet``, so this one has to be fixed before the sale
  family can be upgraded without a manual workaround; the model rename belongs in
  a script of ``hr`` and is declared in ``apriori.py:renamed_models`` already.
+ ``crm_iap_mine``: ``data/crm.iap.lead.industry.csv`` replaces the whole
  industry list with new ids (23 records in 19.0, 83 in 20.0, 81 of them
  unknown to the database) under ``crm_iap_lead_industry_name_uniq``.
+ ``hr_work_entry``: ``data/hr_work_entry_type_data.xml`` goes from 118 to 632
  ids, of which 540 are fresh.
+ ``stock_account`` -> ``account``: the Inventory Valuation client action moved
  between addons (``account/report/account_stock_valuation_report.xml``) and
  stops on ``ir_act_client_path_unique``. Both addons still exist, so this is not
  a module move: ``account`` needs a script that frees the id.
+ ``res.bank`` is dropped by 20.0 together with its data files and
  ``res.partner.bank#bank_id``, so the bank master data of 19.0 has no
  successor; nothing in this coverage migrates it.

``crm_iap_mine``, ``hr_work_entry`` and the ``res.bank`` removal are not reached by
the sale-family test run, which restricts the database to the dependency closure of
the sale family first: an uninstalled addon does not reload its data files. The
three blockers above them (``mail``, the ``hr`` model rename and the
``stock_account`` -> ``account`` move) are worked around with raw sql in the test rig
instead of a script, because they belong to other modules. None of them can be
avoided by narrowing ``--update`` in a real upgrade either:
``ir_module_module.update_list()`` version bumps every installed module against the
20.0 tree, so all of them take the ``'to upgrade'`` branch of
``loading.load_module_graph`` and reload their data.

