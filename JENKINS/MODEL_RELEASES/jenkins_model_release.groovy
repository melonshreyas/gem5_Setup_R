// Jenkins pipeline for collecting a validated gem5 model release.

pipeline {
    agent any

    parameters {
        choice(
            name: 'MODEL_UNIT_NAME',
            choices: [
                'IFU', 'BPU', 'IDU', 'DISPATCH_UNIT', 'RENAME_UNIT', 'ISSUE_QUEUE',
                'COMPLETION_UNIT', 'FXU', 'ALU', 'FPU', 'VSX', 'CRU', 'LSU',
                'EA_GENERATION', 'L1_ICACHE', 'L1_DCACHE', 'L2_CACHE', 'DTLB',
                'PREFETCH_ENGINE', 'MEMORY_CONTROLLER', 'COHERENCE_ENGINE',
                'NEST_INTERCONNECT', 'PCIe_CONTROLLER', 'CAPI_INTERFACE',
                'NVLINK_INTERFACE', 'SMT_SCHEDULER'
            ],
            description: 'Required POWER9 pipeline/model unit.'
        )
        string(name: 'BRANCH', defaultValue: 'stable', description: 'Required Git branch to clone.')
        choice(name: 'COMPILE_TARGET', choices: ['opt', 'debug'], description: 'gem5 binary to compile.')
        choice(name: 'CHIP_NAME', choices: ['ALL', 'CHIP_1', 'CHIP_2', 'CHIP_3'], description: 'Optional chip filter. ALL selects every configured chip.')
        string(name: 'TESTCASE', defaultValue: 'ALL', description: 'Optional comma-separated testcase filter. ALL selects every testcase in chip_configuration.json.')
        string(name: 'CHIP_CONFIGURATION', defaultValue: '', description: 'Optional chip_configuration.json path. Defaults to SMOKE configuration.')
        booleanParam(name: 'DRY_RUN', defaultValue: false, description: 'Print and archive the release plan without cloning, compiling, simulating, emailing, or creating a release version.')
        booleanParam(name: 'SEND_EMAIL', defaultValue: false, description: 'Send the unit/version HTML release report by email.')
        string(name: 'SMTP_SERVER', defaultValue: '', description: 'SMTP server hostname. Leave empty to use SMTP_SERVER environment setting.')
        string(name: 'SENDER_EMAIL', defaultValue: '', description: 'Sender email address.')
        password(name: 'SENDER_PASSWORD', defaultValue: '', description: 'SMTP password or app password.')
        text(name: 'RECIPIENT_EMAILS', defaultValue: '', description: 'Comma-separated recipient email addresses.')
        text(name: 'SUMMARY', defaultValue: '', description: 'Required release summary.')
        text(name: 'FIXES', defaultValue: '', description: 'Required list of fixes and changes.')
        string(name: 'REPO_URL', defaultValue: 'https://github.com/melonshreyas/gem5_Setup_R.git', description: 'Repository to clone for the release.')
    }

    environment {
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
        PYTHON_BIN = 'python3'
        RELEASE_SCRIPT = "${env.WORKSPACE}/JENKINS/MODEL_RELEASES/model_release.py"
        RELEASE_ROOT = '/Users/diya/Documents/JENKINS/HISTORY/MODEL_RELEASES'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('CHECK_REQUIRED_INPUTS') {
            steps {
                script {
                    def required = [
                        'MODEL_UNIT_NAME': params.MODEL_UNIT_NAME,
                        'BRANCH': params.BRANCH,
                        'SUMMARY': params.SUMMARY,
                        'FIXES': params.FIXES,
                        'REPO_URL': params.REPO_URL
                    ]
                    def missing = required.findAll { key, value -> !value?.toString()?.trim() }.keySet()
                    if (missing) {
                        error("RELEASE BLOCKED: missing required parameters: ${missing.join(', ')}")
                    }
                    echo '[RELEASE] Required inputs validated.'
                }
            }
        }

        stage('CHECKOUT_SOURCE') {
            steps {
                echo '[RELEASE] Checking out the release source repository.'
                checkout scm
            }
        }

        stage('PREPARE_RELEASE_DIRECTORY') {
            steps {
                sh '''
                    set -eu
                    mkdir -p "$RELEASE_ROOT"
                    "$PYTHON_BIN" --version
                    test -f "$RELEASE_SCRIPT"
                '''
            }
        }

        stage('CLONE_RELEASE_SOURCE') {
            steps {
                echo '[RELEASE] Python collector will clone or update the selected branch.'
            }
        }

        stage('COLLECT_RELEASE_METADATA') {
            steps {
                sh '''
                    #!/bin/bash
                    set -eu
                    ARGS=(
                        --model-unit-name "$MODEL_UNIT_NAME"
                        --compile "$COMPILE_TARGET"
                        --chip-name "$CHIP_NAME"
                        --testcase "$TESTCASE"
                        --branch "$BRANCH"
                        --summary "$SUMMARY"
                        --fixes "$FIXES"
                        --repo-url "$REPO_URL"
                    )
                    if [ -n "$CHIP_CONFIGURATION" ]; then
                        ARGS+=(--chip-configuration "$CHIP_CONFIGURATION")
                    fi
                    if [ "$DRY_RUN" = "true" ]; then
                        ARGS+=(--dry-run)
                    fi
                    if [ "$SEND_EMAIL" = "true" ]; then
                        ARGS+=(--send-email)
                        [ -n "$SMTP_SERVER" ] && ARGS+=(--smtp-server "$SMTP_SERVER")
                        [ -n "$SENDER_EMAIL" ] && ARGS+=(--sender-email "$SENDER_EMAIL")
                        [ -n "$SENDER_PASSWORD" ] && ARGS+=(--sender-password "$SENDER_PASSWORD")
                        IFS=',' read -r -a RECIPIENTS <<< "$RECIPIENT_EMAILS"
                        for recipient in "${RECIPIENTS[@]}"; do
                            [ -n "${recipient// /}" ] && ARGS+=(--recipient-email "$recipient")
                        done
                    fi
                    "$PYTHON_BIN" "$RELEASE_SCRIPT" "${ARGS[@]}"
                '''
            }
        }

        stage('VALIDATE_DRY_RUN_OUTPUT') {
            when {
                expression { return params.DRY_RUN }
            }
            steps {
                sh '''
                    set -eu
                    test -s model_release_dry_run/dry_run_manifest.json
                    test -s model_release_dry_run/dry_run.log
                    "$PYTHON_BIN" -m json.tool model_release_dry_run/dry_run_manifest.json >/dev/null
                '''
            }
        }

        stage('VALIDATE_RELEASE_MANIFEST') {
            when {
                expression { return !params.DRY_RUN }
            }
            steps {
                sh '''
                    set -eu
                    RELEASE_DIR=$(find "$RELEASE_ROOT/$MODEL_UNIT_NAME" -mindepth 1 -maxdepth 1 -type d -name "${MODEL_UNIT_NAME}_*" -print | sort | tail -n 1)
                    test -n "$RELEASE_DIR"
                    test -s "$RELEASE_DIR/release_manifest.json"
                    test -s "$RELEASE_DIR/RELEASE_NOTES.md"
                    test -s "$RELEASE_DIR/release_report.html"
                    "$PYTHON_BIN" -m json.tool "$RELEASE_DIR/release_manifest.json" >/dev/null
                '''
            }
        }

        stage('ARCHIVE_RELEASE_ARTIFACTS') {
            when {
                expression { return !params.DRY_RUN }
            }
            steps {
                sh '''
                    set -eu
                    rm -rf release_artifacts
                    mkdir -p release_artifacts
                    RELEASE_DIR=$(find "$RELEASE_ROOT/$MODEL_UNIT_NAME" -mindepth 1 -maxdepth 1 -type d -name "${MODEL_UNIT_NAME}_*" -print | sort | tail -n 1)
                    cp -R "$RELEASE_DIR/." release_artifacts/
                '''
                archiveArtifacts artifacts: 'release_artifacts/**/*.json, release_artifacts/**/*.md, release_artifacts/**/*.html', allowEmptyArchive: false
            }
        }

        stage('ARCHIVE_DRY_RUN_PLAN') {
            when {
                expression { return params.DRY_RUN }
            }
            steps {
                archiveArtifacts artifacts: 'model_release_dry_run/dry_run_manifest.json, model_release_dry_run/dry_run.log', allowEmptyArchive: false
            }
        }
    }

    post {
        success {
            echo '[RELEASE] MODEL RELEASE COMPLETED.'
        }
        failure {
            echo '[RELEASE] MODEL RELEASE BLOCKED. Check required inputs and the first failing stage.'
        }
    }
}
