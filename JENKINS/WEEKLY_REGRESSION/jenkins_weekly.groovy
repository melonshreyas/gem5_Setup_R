// Basic Jenkins pipeline for the gem5 smoke workflow.
// This script can be loaded into a Jenkins Pipeline job and used to run the
// workflow with configurable build, chip-selection, and reporting options.

pipeline {
    agent any

    parameters {
        string(
            name: 'BRANCH',
            defaultValue: 'stable',
            description: 'Git branch to check out before running the smoke workflow.'
        )
        string(
            name: 'INPUT_DIR',
            defaultValue: '',
            description: 'Root directory of the gem5 repository checkout. Leave empty to use the Jenkins workspace.'
        )
        string(
            name: 'OUTPUT_DIR',
            defaultValue: '',
            description: 'Optional output directory for the smoke run. Leave empty to let the script auto-create one.'
        )
        string(
            name: 'CHIP_CONFIGURATION',
            defaultValue: '',
            description: 'Absolute path to chip_configuration.json. Leave empty to use JENKINS/WEEKLY_REGRESSION/chip_configuration.json inside the workspace.'
        )
        choice(
            name: 'COMPILE_TARGET',
            choices: ['opt', 'debug'],
            description: 'gem5 build target to compile.'
        )
        // NOTE: chip names here are static seed values — add new chips to this list manually when chip_configuration.json changes.
        // The Discover Chips stage auto-updates these choices from the second build onwards.
        choice(
            name: 'CHIP_NAME',
            choices: ['ALL', 'CHIP_1', 'CHIP_2', 'CHIP_3'],
            description: 'Chip to run. ALL (default) runs every chip. Discover Chips stage updates this list automatically.'
        )
        booleanParam(
            name: 'SKIP_COMPILATION',
            defaultValue: false,
            description: 'Skip the compilation stage and reuse the existing build if possible.'
        )
        booleanParam(
            name: 'SKIP_SIMULATION',
            defaultValue: false,
            description: 'Skip simulation but still generate the summary and report files.'
        )
        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'Print the planned commands without executing them.'
        )
        booleanParam(
            name: 'SEND_EMAIL',
            defaultValue: false,
            description: 'Send the generated history report by email after the run finishes.'
        )
    }

    environment {
        // Homebrew bin must be explicit — Jenkins runs with a minimal PATH that omits it.
        PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${env.PATH}"
        PYTHON_BIN = 'python3'
        REPO_ROOT = "${env.WORKSPACE}"
        WEEKLY_REPO_URL = 'https://github.com/melonshreyas/gem5_Setup_R.git'
        WEEKLY_INPUT_DIR = "${env.WORKSPACE}"
        WEEKLY_OUTPUT_DIR = "/Users/diya/Documents/JENKINS/WEEKLY_REGRESSION/WEEKLY_BUILD_${env.BUILD_NUMBER}"
        WEEKLY_HISTORY_DIR = '/Users/diya/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION'
        WEEKLY_CONFIG = "${env.WORKSPACE}/JENKINS/WEEKLY_REGRESSION/chip_configuration.json"
        WEEKLY_SCRIPT = "${env.WORKSPACE}/JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py"
        BUILD_TAG_VALUE = "${env.BUILD_TAG}"
        BUILD_ID_VALUE = "${env.BUILD_ID}"
        JOB_NAME_VALUE = "${env.JOB_NAME}"
        NODE_NAME_VALUE = "${env.NODE_NAME}"
        GIT_COMMIT_VALUE = "${env.GIT_COMMIT}"
        GIT_BRANCH_VALUE = "${env.GIT_BRANCH}"
        SMTP_SERVER = ''
        SENDER_EMAIL = ''
        SENDER_PASSWORD = ''
        SMTP_RECIPIENTS = ''
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                echo '[Pipeline] Starting checkout stage.'
                echo "[Pipeline] Workspace: ${env.WORKSPACE}"
                echo "[Pipeline] Branch parameter: ${params.BRANCH}"
                script {
                    // CSS is generated as an external file and published with HTML assets.
                    // Avoid runtime JVM property changes here; Jenkins sandbox may block them.
                    echo '[Pipeline] Skipping runtime CSP override; using external CSS assets for report styling.'
                    try {
                        echo '[Pipeline] Attempting checkout scm.'
                        checkout scm
                        echo '[Pipeline] checkout scm completed successfully.'
                    } catch (Exception exc) {
                        echo "[Pipeline] SCM checkout not available in this Jenkins context: ${exc.getMessage()}"
                        dir(env.WORKSPACE) {
                            echo '[Pipeline] Falling back to local workspace inspection.'
                            sh 'pwd && ls -la'
                        }
                    }
                }
            }
        }

        stage('Discover Chips') {
            steps {
                script {
                    // Read chip names from chip_configuration.json and update CHIP_NAME choices for the next build.
                    // Discovery is best-effort: if the repo/config is not present yet, this build continues.
                    def configuredPath = params.CHIP_CONFIGURATION?.trim()
                        ? (params.CHIP_CONFIGURATION.startsWith('/') ? params.CHIP_CONFIGURATION : "${env.WORKSPACE}/${params.CHIP_CONFIGURATION}")
                        : ''
                    def candidatePaths = []
                    if (configuredPath) {
                        candidatePaths << configuredPath
                    }
                    candidatePaths << env.WEEKLY_CONFIG
                    candidatePaths << "${env.WORKSPACE}/JENKINS/SMOKE/chip_configuration.json"

                    def chipConfigPath = candidatePaths.find { path -> path?.trim() && fileExists(path) }
                    if (!chipConfigPath) {
                        echo "[Pipeline] CHIP discovery skipped: no chip_configuration.json found in candidates: ${candidatePaths.join(', ')}"
                        echo '[Pipeline] This is expected on first run before repository checkout/clone; parameter choices stay unchanged for this build.'
                        return
                    }

                    def chipNamesRaw = sh(
                        script: "${env.PYTHON_BIN} -c \"import json; cfg=json.load(open('${chipConfigPath}')); print('\\n'.join(['ALL']+sorted(cfg.keys())))\"",
                        returnStdout: true
                    ).trim()

                    def chipList = chipNamesRaw.split('\n').toList()
                    echo "[Pipeline] Available chips in ${chipConfigPath}:"
                    chipList.each { echo "[Pipeline]   - ${it}" }

                    // Update CHIP_NAME parameter choices so future builds show a dropdown; ALL is the default.
                    properties([
                        parameters([
                            string(name: 'BRANCH', defaultValue: params.BRANCH ?: 'stable',
                                description: 'Git branch to check out before running the weekly workflow.'),
                            string(name: 'INPUT_DIR', defaultValue: '',
                                description: 'Root directory of the gem5 repository checkout. Leave empty to use the Jenkins workspace.'),
                            string(name: 'OUTPUT_DIR', defaultValue: '',
                                description: 'Optional output directory for the weekly run. Leave empty to let the script auto-create one.'),
                            string(name: 'CHIP_CONFIGURATION', defaultValue: '',
                                description: 'Absolute path to chip_configuration.json. Leave empty to use JENKINS/WEEKLY_REGRESSION/chip_configuration.json inside the workspace.'),
                            choice(name: 'COMPILE_TARGET', choices: ['opt', 'debug'],
                                description: 'gem5 build target to compile.'),
                            choice(name: 'CHIP_NAME', choices: chipList,
                                description: 'Chip to run. ALL (default) runs every configured chip. Populated automatically from chip_configuration.json.'),
                            booleanParam(name: 'SKIP_COMPILATION', defaultValue: false,
                                description: 'Skip the compilation stage and reuse the existing build if possible.'),
                            booleanParam(name: 'SKIP_SIMULATION', defaultValue: false,
                                description: 'Skip simulation but still generate the summary and report files.'),
                            booleanParam(name: 'DRY_RUN', defaultValue: false,
                                description: 'Print the planned commands without executing them.'),
                            booleanParam(name: 'SEND_EMAIL', defaultValue: false,
                                description: 'Send the generated history report by email after the run finishes.')
                        ])
                    ])
                    echo '[Pipeline] CHIP_NAME parameter updated with chip choices for the next build.'
                }
            }
        }

        stage('Prepare Environment') {
            steps {
                echo '[Pipeline] Preparing Python environment and workspace folders.'
                sh '''
                    set -e
                    echo "[Shell] Python executable: ${PYTHON_BIN}"
                    ${PYTHON_BIN} --version
                    echo "[Shell] Creating output directory: $WEEKLY_OUTPUT_DIR"
                    mkdir -p "$WEEKLY_OUTPUT_DIR"
                    if [ -d "$WORKSPACE/.git" ]; then
                        echo "[Shell] Workspace already contains a Git checkout."
                    else
                        echo "[Shell] Cloning repository: $WEEKLY_REPO_URL"
                        git clone --recursive "$WEEKLY_REPO_URL" "$WORKSPACE"
                    fi
                    cd "$WORKSPACE"
                    echo "[Shell] Updating submodules."
                    git submodule update --init --recursive
                    echo "[Shell] Checking out branch: $BRANCH"
                    git checkout "$BRANCH"
                    echo "[Shell] Current repository status:"
                    git status --short --branch
                '''
            }
        }

        stage('Run Smoke Workflow') {
            steps {
                script {
                    echo '[Pipeline] Preparing smoke workflow arguments.'
                    def cliArgs = []
                    def inputDir = params.INPUT_DIR?.trim() ? params.INPUT_DIR : env.WEEKLY_INPUT_DIR
                    // Always resolve chip config to an absolute path.
                    def chipConfigRaw = params.CHIP_CONFIGURATION?.trim() ?: ''
                    def chipConfig = chipConfigRaw
                        ? (chipConfigRaw.startsWith('/') ? chipConfigRaw : "${env.WORKSPACE}/${chipConfigRaw}")
                        : env.WEEKLY_CONFIG
                    def outputDir = params.OUTPUT_DIR?.trim() ? params.OUTPUT_DIR : env.WEEKLY_OUTPUT_DIR
                    def smokeScript = env.WEEKLY_SCRIPT ?: "${env.WORKSPACE}/JENKINS/WEEKLY_REGRESSION/jenkins_weekly.py"

                    echo "[Pipeline] Input directory: ${inputDir}"
                    echo "[Pipeline] Chip configuration: ${chipConfig}"
                    echo "[Pipeline] Output directory: ${outputDir}"
                    echo "[Pipeline] Smoke script: ${smokeScript}"
                    echo "[Pipeline] Compile target: ${params.COMPILE_TARGET}"
                    echo "[Pipeline] Chip name: ${params.CHIP_NAME ?: 'ALL'}"
                    echo "[Pipeline] Skip compilation: ${params.SKIP_COMPILATION}"
                    echo "[Pipeline] Skip simulation: ${params.SKIP_SIMULATION}"
                    echo "[Pipeline] Dry run: ${params.DRY_RUN}"
                    echo "[Pipeline] Send email: ${params.SEND_EMAIL}"

                    cliArgs << "--input-dir"
                    cliArgs << inputDir
                    cliArgs << "--branch"
                    cliArgs << params.BRANCH
                    cliArgs << "--chip-configuration"
                    cliArgs << chipConfig
                    cliArgs << "--compile"
                    cliArgs << params.COMPILE_TARGET

                    if (outputDir?.trim()) {
                        cliArgs << "--output-dir"
                        cliArgs << outputDir
                    }

                    // Pass CHIP_NAME to the script; ALL tells the script to run every configured chip.
                    if (params.CHIP_NAME?.trim() && params.CHIP_NAME.trim().toUpperCase() != 'ALL') {
                        cliArgs << "--chip-name"
                        cliArgs << params.CHIP_NAME.trim()
                    } else {
                        cliArgs << "--chip-name"
                        cliArgs << "ALL"
                    }

                    if (params.SKIP_COMPILATION) {
                        cliArgs << "--skip-compilation"
                    }

                    if (params.SKIP_SIMULATION) {
                        cliArgs << "--skip_simulation"
                    }

                    if (params.DRY_RUN) {
                        cliArgs << "--dry_run"
                    }

                    if (params.SEND_EMAIL) {
                        cliArgs << "--send-email"
                        if (env.SMTP_SERVER?.trim()) {
                            cliArgs << "--smtp-server"
                            cliArgs << env.SMTP_SERVER
                        }
                        if (env.SENDER_EMAIL?.trim()) {
                            cliArgs << "--sender-email"
                            cliArgs << env.SENDER_EMAIL
                        }
                        if (env.SENDER_PASSWORD?.trim()) {
                            cliArgs << "--sender-password"
                            cliArgs << env.SENDER_PASSWORD
                        }
                        if (env.SMTP_RECIPIENTS?.trim()) {
                            cliArgs << "--recipient-email"
                            cliArgs << env.SMTP_RECIPIENTS
                        }
                    }

                    def cmd = "${env.PYTHON_BIN} '${smokeScript}'"
                    for (arg in cliArgs) {
                        cmd += " '${arg.replace("'", "'\\''")}'"
                    }

                    echo "[Pipeline] Running smoke workflow with command: ${cmd}"
                    sh cmd
                    echo '[Pipeline] Smoke workflow command completed.'
                }
            }
        }
    }

    post {
        always {
            echo 'Publishing smoke workflow artifacts and reports.'
            archiveArtifacts(
                artifacts: '/Users/diya/Documents/JENKINS/WEEKLY_REGRESSION/**/*.html, /Users/diya/Documents/JENKINS/WEEKLY_REGRESSION/**/*.json, /Users/diya/Documents/JENKINS/HISTORY/**/*.html, /Users/diya/Documents/JENKINS/HISTORY/**/*.json',
                allowEmptyArchive: true
            )

            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                includes: '**/*',
                reportDir: '/Users/diya/Documents/JENKINS/HISTORY/WEEKLY_REGRESSION',
                reportFiles: 'jenkins_history_weekly_results.html',
                reportName: 'Smoke History Report'
            ])
        }

        failure {
            echo 'The smoke workflow failed. Inspect the archived logs and reports for details.'
        }
    }
}
