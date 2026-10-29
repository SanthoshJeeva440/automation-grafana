pipeline {
  agent any
  triggers { cron('H 8 * * 5') }
  options { timestamps(); disableConcurrentBuilds(); buildDiscarder(logRotator(numToKeepStr: '20')) }
  environment {
    INFLUX_URL='https://us-east-1-1.aws.cloud2.influxdata.com'
    INFLUX_BUCKET='qa_metrics'
    INFLUX_DATABASE='qa_metrics'
    INFLUX_RETENTION_POLICY='autogen'
    PYTHONUNBUFFERED='1'
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Install dependencies') {
      steps { sh 'python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && pip install -r requirements.txt' }
    }
    stage('Collect versions') {
      steps {
        withCredentials([string(credentialsId: 'influx-cloud-token', variable: 'INFLUX_TOKEN')]) {
          sh '. .venv/bin/activate && python runners/automation_tool_version_runner.py'
        }
      }
    }
    stage('Email upgrades') {
      steps {
        script {
          def report=readJSON file:'upgrade_report.json'
          if (report.upgrades && report.upgrades.size()>0) {
            def rows=report.upgrades.collect { x -> "${x.name} (${x.category}): ${x.previous_version} -> ${x.latest_version}\\n${x.release_url}" }.join('\\n\\n')
            emailext(to:'santhoshjeeva440@gmail.com',subject:"[Automation Version Tracker] ${report.upgrades.size()} upgrade(s) detected",mimeType:'text/plain',body:"Stable upgrades detected.\\n\\nChecked UTC: ${report.checked_at_utc}\\n\\n${rows}\\n\\nBuild: ${env.BUILD_URL}")
          } else { echo 'No upgrades detected; no email sent.' }
        }
      }
    }
  }
  post {
    always { archiveArtifacts artifacts:'upgrade_report.json',allowEmptyArchive:true }
    failure { emailext(to:'santhoshjeeva440@gmail.com',subject:"[Automation Version Tracker] FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",body:"Version tracker failed. Check ${env.BUILD_URL}console") }
  }
}
