// Jenkins pipeline for generating a disk space usage report.

pipeline {
    agent any

    parameters {
        string(name: 'BRANCH', defaultValue: 'stable', description: 'Git branch to check out before running the disk space report.')
        string(name: 'REPO_URL', defaultValue: 'https://github.com/melonshreyas/gem5_Setup_R.git', description: 'Repository containing JENKINS/DISK_SPACE/disk_space_report.py to check out.')
        string(name: 'INPUT_DIR', defaultValue: '', description: 'Required root directory to scan for disk usage.')
        string(name: 'OUTPUT_DIR', defaultValue: '', description: 'Optional output directory for the reports. Leave empty to auto-name it INPUT_DIR/DISK_SPACE/DISK_SPACE_BUILD_<BUILD_NUMBER>.')
        string(name: 'MAX_DEPTH', defaultValue: '', description: 'Optional maximum directory depth to descend into. Leave empty for unlimited depth.')
        string(name: 'TOP_N', defaultValue: '', description: 'Optional: only show the N largest subdirectories per level. Leave empty to show all.')
        booleanParam(name: 'DRY_RUN', defaultValue: false, description: 'Scan and print a preview without writing any report files.')
    }

    environment {
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
        PYTHON_BIN = 'python3'
        DISK_SPACE_SCRIPT = "${env.WORKSPACE}/JENKINS/DISK_SPACE/disk_space_report.py"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '50'))
    }

    stages {
        stage('CHECKOUT_SOURCE') {
            steps {
                echo '[DISK_SPACE] Checking out disk_space_report.py from the source repository.'
                git branch: params.BRANCH, url: params.REPO_URL
            }
        }

        stage('CHECK_REQUIRED_INPUTS') {
            steps {
                script {
                    if (!params.INPUT_DIR?.trim()) {
                        error('DISK SPACE BLOCKED: missing required parameter: INPUT_DIR')
                    }
                    echo '[DISK_SPACE] Required inputs validated.'
                }
            }
        }

        stage('RUN_DISK_SPACE_REPORT') {
            steps {
                script {
                    def cliArgs = ["--input-dir", params.INPUT_DIR.trim()]
                    if (params.OUTPUT_DIR?.trim()) {
                        cliArgs << "--output-dir"
                        cliArgs << params.OUTPUT_DIR.trim()
                    }
                    if (params.MAX_DEPTH?.trim()) {
                        cliArgs << "--max-depth"
                        cliArgs << params.MAX_DEPTH.trim()
                    }
                    if (params.TOP_N?.trim()) {
                        cliArgs << "--top"
                        cliArgs << params.TOP_N.trim()
                    }
                    if (params.DRY_RUN) {
                        cliArgs << "--dry-run"
                    }

                    def cmd = "\"\$PYTHON_BIN\" \"\$DISK_SPACE_SCRIPT\""
                    for (arg in cliArgs) {
                        cmd += " '${arg.replace("'", "'\\''")}'"
                    }

                    echo "[DISK_SPACE] Running: ${cmd}"
                    sh cmd
                    echo '[DISK_SPACE] Report generation completed.'
                }
            }
        }
    }

    post {
        always {
            script {
                if (!params.DRY_RUN) {
                    sh '''
                        set +e
                        if [ -n "${OUTPUT_DIR:-}" ]; then
                            REPORT_DIR="$OUTPUT_DIR"
                        else
                            DISK_SPACE_ROOT="$INPUT_DIR/DISK_SPACE"
                            REPORT_DIR=$(ls -dt "$DISK_SPACE_ROOT"/DISK_SPACE_* 2>/dev/null | head -n 1)
                        fi
                        if [ -n "$REPORT_DIR" ] && [ -f "$REPORT_DIR/disk_space_report.html" ]; then
                            mkdir -p "$WORKSPACE/htmlreports/disk_space"
                            cp -f "$REPORT_DIR/disk_space_report.html" "$WORKSPACE/htmlreports/disk_space/"
                            cp -f "$REPORT_DIR/disk_space_report.css" "$WORKSPACE/htmlreports/disk_space/"
                            cp -f "$REPORT_DIR/disk_space_report.json" "$WORKSPACE/htmlreports/disk_space/"
                            cp -f "$REPORT_DIR/disk_space_tree.txt" "$WORKSPACE/htmlreports/disk_space/"
                        else
                            echo "[DISK_SPACE] No report found at: ${REPORT_DIR:-<empty>}"
                        fi
                        set -e
                    '''
                    archiveArtifacts artifacts: 'htmlreports/disk_space/**/*', allowEmptyArchive: true

                    publishHTML(target: [
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        includes: '**/*',
                        reportDir: 'htmlreports/disk_space',
                        reportFiles: 'disk_space_report.html',
                        reportName: 'Disk Space Report'
                    ])
                }
            }
        }

        failure {
            echo '[DISK_SPACE] Report generation failed. Check INPUT_DIR and the console log for details.'
        }
    }
}
