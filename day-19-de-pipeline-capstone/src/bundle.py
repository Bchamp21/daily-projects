"""Generate a Databricks Asset Bundle job (databricks.yml) from the SAME task list,
so the local DAG and the production job can never drift apart."""
from __future__ import annotations
from dag import Task, topo_order


def to_bundle_yaml(tasks: list[Task], job_name: str = "stock_pipeline",
                   cron: str = "0 30 18 ? * MON-FRI", tz: str = "America/Denver",
                   alert_email: str = "${var.alert_email}") -> str:
    topo_order(tasks)  # validates deps + no cycles before we emit anything
    lines = [
        "bundle:",
        "  name: stock-pipeline",
        "",
        "variables:",
        "  alert_email:",
        "    description: Who gets failure emails",
        "",
        "targets:",
        "  dev:",
        "    mode: development",
        "    default: true",
        "",
        "resources:",
        "  jobs:",
        f"    {job_name}:",
        f"      name: {job_name}",
        "      schedule:",
        f'        quartz_cron_expression: "{cron}"',
        f"        timezone_id: {tz}",
        "      email_notifications:",
        f"        on_failure: [\"{alert_email}\"]",
        "      tasks:",
    ]
    for t in tasks:
        lines.append(f"        - task_key: {t.key}")
        if t.depends_on:
            lines.append("          depends_on:")
            lines += [f"            - task_key: {d}" for d in t.depends_on]
        lines.append(f"          max_retries: {t.max_retries}")
        lines.append("          notebook_task:")
        lines.append(f"            notebook_path: ../{t.notebook}")
    return "\n".join(lines) + "\n"
