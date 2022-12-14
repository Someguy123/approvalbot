#!/usr/bin/env bash
################################################################
#                                                              #
#              Production runner script for:                   #
#                                                              #
#                  Approval Bot for Discord                    #
#            (C) 2022 Someguy123   GNU AGPL v3                 #
#                                                              #
#      Github Repo: https://github.com/Someguy123/approvalbot  #
#                                                              #
################################################################
######
# Directory where the script is located, so we can source files regardless of where PWD is
######

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:${PATH}"
export PATH="${HOME}/.local/bin:${PATH}"

cd "$DIR"


BOLD="" RED="" GREEN="" YELLOW="" BLUE="" MAGENTA="" CYAN="" WHITE="" RESET=""
if [ -t 1 ]; then
    BOLD="$(tput bold)" RED="$(tput setaf 1)" GREEN="$(tput setaf 2)" YELLOW="$(tput setaf 3)" BLUE="$(tput setaf 4)"
    MAGENTA="$(tput setaf 5)" CYAN="$(tput setaf 6)" WHITE="$(tput setaf 7)" RESET="$(tput sgr0)"
fi

# easy coloured messages function
# written by @someguy123
msg() {
    # usage: msg [color] message
    if [[ "$#" -eq 0 ]]; then
        echo ""
        return
    fi
    if [[ "$#" -eq 1 ]]; then
        echo -e "$1"
        return
    fi

    ts="no"
    if [[ "$#" -gt 2 ]] && [[ "$1" == "ts" ]]; then
        ts="yes"
        shift
    fi
    if [[ "$#" -gt 2 ]] && [[ "$1" == "bold" ]]; then
        echo -n "${BOLD}"
        shift
    fi
    [[ "$ts" == "yes" ]] && _msg="[$(date +'%Y-%m-%d %H:%M:%S %Z')] ${@:2}" || _msg="${@:2}"

    case "$1" in
        bold) echo -e "${BOLD}${_msg}${RESET}" ;;
        [Bb]*) echo -e "${BLUE}${_msg}${RESET}" ;;
        [Yy]*) echo -e "${YELLOW}${_msg}${RESET}" ;;
        [Rr]*) echo -e "${RED}${_msg}${RESET}" ;;
        [Gg]*) echo -e "${GREEN}${_msg}${RESET}" ;;
        *) echo -e "${_msg}" ;;
    esac
}

has-command() {
    command -v "$@" &> /dev/null
}

run-bot() {
    PIPENV_VERBOSITY=-1 pipenv run python3 -m approvalbot "$@"
}

case "$1" in
    service|install-service|install_service|systemd)
        msg ts bold green "Attempting to install systemd service"
        if (( EUID == 0 )); then
            cp -v *.service /etc/systemd/system/
            msg ts bold green " >> Reloading systemd"
            systemctl daemon-reload
            msg ts bold green " >> Enabling and starting the service"
            systemctl enable --now approvalbot
        else
            msg bold yellow "You are not root, so we'll try to use 'sudo' to install it - you may be prompted for your user password"
            sudo cp -v *.service /etc/systemd/system/
            msg ts bold green " >> Reloading systemd"
            sudo systemctl daemon-reload
            msg ts bold green " >> Enabling and starting the service"
            sudo systemctl enable --now approvalbot
        fi
        msg ts bold green " [+++] FINISHED. You can check the status of the service with: systemctl status approvalbot"
        ;;
    update | upgrade)
        msg ts bold green " >> Updating files from Github"
        git pull
        msg ts bold green " >> Updating Python packages"
        pipenv update
        msg ts bold green " +++ Finished"
        echo
        msg bold yellow "Post-update info:"
        msg yellow "Please **become root**, and read the below additional steps to finish your update"

        msg yellow " - You may wish to update your systemd service files in-case there are any changes:"
        msg blue "\t cp -v *.service /etc/systemd/system/"
        msg blue "\t systemctl daemon-reload"

        msg yellow " - Please remember to restart all ApprovalBot services AS ROOT like so:"
        msg blue "\t systemctl restart approvalbot"
        ;;
    install)
        if ! has-command pipenv; then
            if ! has-command python3; then
                msg bold red " [!!!] ERROR: Could not find 'python3' - please install python 3.x! (3.8 or newer recommended)"
                exit 2
            fi
            msg bold yellow " [WARN] pipenv is not installed. Attempting to install pipenv..."
            if (( EUID == 0 )); then
                python3 -m pip install -U pipenv
                _ret=$?
            else
                msg yellow " [...] As you're not root, will try to install pipenv locally..."
                python3 -m pip install --local -U pipenv
                _ret=$?
            fi
            if (( _ret )); then
                msg bold red " [!!!] ERROR: pip returned a non-zero error code, failed to install pipenv... Please try installing it manually as root using: python3 -m pip install -U pipenv"
                return $_ret
            fi
        fi
        msg ts bold green " >> Running pipenv install"
        pipenv install --ignore-pipfile --dev
        _ret=$?
        if (( _ret )); then
            msg bold yellow " [!!!] WARNING: pipenv returned a non-zero error code, the environment may not have been setup correctly..."
        fi
        msg magenta "\n >> Now that the pipenv environment has been setup, if you want to run this bot as a background service, you should install the systemd service file"
        msg magenta " >> You can do that by running: ${BOLD}$0 service"
        msg magenta " >> We recommend running that command as root - if your user has sudo privileges, it may work from the current user.\n"
        return $_ret
        ;;
    serve* | runserv* | start* | run* | bot | exec*)
        # Override these defaults inside of `.env`
        shift
        run-bot "$@"
        ;;
    *)
        msg bold red "Unknown command.\n"
        msg bold green "Discord Approval Bot - (C) 2022 Someguy123"
        msg bold green "    Source: https://github.com/Someguy123/approvalbot\n"
        msg green "Available run.sh commands:\n"
        msg yellow "\t install - Install the pipenv virtualenv with required python packages"
        msg yellow "\t service - Install and enable/start the systemd service for approvalbot"
        msg yellow "\t update - Upgrade your ApprovalBot installation"
        msg yellow "\t start - Start the production discord bot"
        msg green "\nAdditional aliases for the above commands:\n"
        msg yellow "\t upgrade - Alias for 'update'"
        msg yellow "\t serve, runserver, run, exec, bot - Alias for 'start'"

        ;;
esac