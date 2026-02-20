#!/usr/bin/env bash
# lmgate-manager — control plane for the LMGate stack (nginx + lmgate services)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

usage() {
    cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  start     Build and start all services
  stop      Stop and remove all services
  restart   Full restart (stop + start)
  reload    Reload nginx config and restart lmgate service
  status    Show service status and health
  logs      Tail service logs (Ctrl-C to stop)

Options:
  -h, --help  Show this help message
EOF
}

log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

check_prerequisites() {
    if ! command -v docker &>/dev/null; then
        log_error "docker is not installed or not in PATH"
        exit 1
    fi
    if ! docker compose version &>/dev/null; then
        log_error "docker compose plugin is not available"
        exit 1
    fi
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose.yaml not found at $PROJECT_ROOT"
        exit 1
    fi
}

compose() {
    docker compose -f "$COMPOSE_FILE" --project-directory "$PROJECT_ROOT" "$@"
}

cmd_start() {
    log_info "Building and starting LMGate stack..."
    compose up -d --build
    log_ok "LMGate stack is up"
}

cmd_stop() {
    log_info "Stopping LMGate stack..."
    compose down
    log_ok "LMGate stack stopped"
}

cmd_restart() {
    log_info "Restarting LMGate stack..."
    compose down
    compose up -d --build
    log_ok "LMGate stack restarted"
}

cmd_reload() {
    log_info "Reloading LMGate stack..."

    if compose ps --format json | grep -q '"nginx"'; then
        log_info "Reloading nginx configuration..."
        compose exec nginx nginx -s reload
        log_ok "nginx config reloaded"
    else
        log_warn "nginx container is not running — skipping nginx reload"
    fi

    if compose ps --format json | grep -q '"lmgate"'; then
        log_info "Restarting lmgate service..."
        compose restart lmgate
        log_ok "lmgate service restarted"
    else
        log_warn "lmgate container is not running — skipping lmgate restart"
    fi

    log_ok "Reload complete"
}

cmd_status() {
    log_info "LMGate stack status:"
    echo ""
    compose ps
    echo ""

    if compose ps --format json | grep -q '"lmgate"'; then
        local health
        health=$(docker inspect --format='{{.State.Health.Status}}' \
            "$(compose ps -q lmgate)" 2>/dev/null || echo "unknown")
        log_info "lmgate health: $health"
    else
        log_warn "lmgate container is not running"
    fi
}

cmd_logs() {
    log_info "Tailing logs (Ctrl-C to stop)..."
    compose logs -f --tail=100
}

main() {
    if [[ $# -eq 0 ]]; then
        usage
        exit 1
    fi

    case "${1}" in
        -h|--help)
            usage
            exit 0
            ;;
        start|stop|restart|reload|status|logs)
            check_prerequisites
            "cmd_${1}"
            ;;
        *)
            log_error "Unknown command: ${1}"
            usage
            exit 1
            ;;
    esac
}

main "$@"
