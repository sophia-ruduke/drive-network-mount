import sh
import requests
import regex
from http import HTTPStatus

status = "gateway_status"
# hard-coded absolute path not ideal
index_path = "/usr/local/bin/startup/snap-webpage/gw-offline.html"


def update_url():
    # get project url from snap config
    project_url = sh.snap("get", "wpe-webkit-mir-kiosk", "url")

    # cut out project from url to get base gateway url
    gateway_url = regex.search(".*:+[0-9]", project_url).group()
    status_url = f"{gateway_url}/StatusPing"

    try:
        current_status = requests.get(status_url).status_code
    # GET throws errors when gateway is offline
    except Exception:
        current_status = HTTPStatus.GATEWAY_TIMEOUT

    previous_status = int(sh.echo(f"${status}"))
    if previous_status != current_status:
        # change url to js file if gw state is anything but OK
        if current_status != HTTPStatus.OK:
            project_url = f"file://{index_path}"

        # else just set it back to project url to force snap to refresh
        sh.snap("set", "wpe-webkit-mir-kiosk", f"url={project_url}")
        sh.export(f"{status}={current_status}")


if __name__ == "__main__":
    update_url()