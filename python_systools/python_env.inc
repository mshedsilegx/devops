#!/bin/bash

# -------------------------------------
#  /var/opt/apps/system/python_env.inc
#  v1.0.3xg  2025/10/14  XDG
# -------------------------------------
# python job executor, with enforcing correct environment

# ----- System Environment -----
source /opt/scripts/settings.sh

function pyEnvInit() {
  PYTHON_TAG="${PYTHON_ID//./}"
  PYTHONHOME="${WEBAPPS_BASE}/python${PYTHON_TAG}"
  PYTHON_PLATFORM="/var/opt/python${PYTHON_TAG}"
  PYTHON="${PYTHONHOME}/bin/python${PYTHON_ID}${PYTHON_MODEL_ID}"
  PYTHON_APP_MODULES="${PYTHONHOME}/lib/modules${PYTHON_ID}${PYTHON_MODEL_ID}"

  PATH="${PYTHONHOME}/bin:${PATH}"

  LD_LIBRARY_PATH="${PYTHONHOME}/lib"
  PKG_CONFIG_PATH=${PYTHONHOME}/lib/pkgconfig
  PYTHONPATH="${PYTHON_APP_MODULES}:${APP_PYTHONPATH}:${PYTHONHOME}/lib/python${PYTHON_ID}${PYTHON_MODEL_ID}"

  if ! [ -d "${PYTHONHOME}" ] || ! [ -x "${PYTHON}" ] || ! [ -d "${PKG_CONFIG_PATH}" ] || ! [ -d "${LD_LIBRARY_PATH}" ];then
    echo "ERROR: Invalid python environment, aborting execution"
    return 1
  fi
  [[ "$*" =~ "--env-display" ]] && env | grep -E "^PYTHON|^PKG|^LD" | sort

}

function pyEnvReset() {
  unset PYTHON_TAG PYTHONHOME PYTHON_PLATFORM PYTHON LD_LIBRARY_PATH PKG_CONFIG_PATH
}


# ----- Main -----
if [[ ! "$0" =~ "python_env.sh" ]];then
  # script is sourced
  PYTHON_ID="$1"
  if [[ -z "${PYTHON_ID}" || ! "${PYTHON_ID}" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    echo "ERROR: Invalid python ID"
    return 2
  fi

  PYTHON_MODEL="$2"
  if [[ -z "${PYTHON_MODEL}" ]] || ! [[ "${PYTHON_MODEL}" = "mt" || "${PYTHON_MODEL}" = "gil" ]]; then
    echo "ERROR: Invalid python model, must be mt (freethreaded) or gil (global lock, single threaded)"
    return 2
  fi

  if [ "${PYTHON_MODEL}" == "mt" ];then
    PYTHON_MODEL_ID="t"
    PYTHON_MODEL_LABEL="MT"
  else
    PYTHON_MODEL_ID=""
    PYTHON_MODEL_LABEL="GIL"
  fi


  case "$*" in
    *--env-load*)
      pyEnvInit $*
    ;;
    *--env-reset*)
      pyEnvReset
    ;;
  esac
else
  echo "ERROR: Invalid python environment, script must be sourced"
  exit 3
fi
