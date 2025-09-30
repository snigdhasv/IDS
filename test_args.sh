#!/bin/bash
main() {
    echo "Args received: $@"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --traffic-mode)
                echo "Found traffic-mode: $2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}
main "$@"
