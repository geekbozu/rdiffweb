pipeline {
    environment {
        NEXUS = credentials("local-nexus")
        GITLAB = credentials("gitlab-jenkins")
        GITHUB = credentials("github")
        PYPI = credentials("ikus060-pypi")
    }
    parameters {
        booleanParam(defaultValue: false, description: 'Generate a release build with a tagged version.', name: 'Release')
        booleanParam(defaultValue: false, description: 'Promote build for production.', name: 'Promote')
    }
    agent {
        docker {
            image 'ikus060/docker-debian-py2-py3:jessie'
        }
    }
    stages {
        stage ('Setup') {
            steps {
                sh 'apt-get update && apt-get -qq install python-pysqlite2 libldap2-dev libsasl2-dev rdiff-backup node-less'
                sh 'pip install pip setuptools tox --upgrade'
            }
        }
        stage ('Build') {
            steps {
                sh 'python setup.py build'
            }
        }
        stage ('Parallel Test') {
            steps {
                script {
                
                    def axisImages = ['jessie', 'stretch']
                    def axisPython = ['py27', 'py3']
                    def axisCherrypy = ['cherrypy14']
                    //def axisCherrypy = ['cherrypy35','cherrypy4','cherrypy5','cherrypy6','cherrypy7','cherrypy8','cherrypy9','cherrypy10','cherrypy11','cherrypy12','cherrypy13','cherrypy14']
                    
                    
                    def builders = [:]
                    for (x in axisImages) {
                    for (y in axisPython) {
                    for (z in axisCherrypy) {
                        // Need to bind the label variable before the closure - can't do 'for (label in labels)'
                        def image = x 
                        def python = y
                        def cherrypy = z
                        def env = "${python}-${cherrypy}"
                    
                        // Create a map to pass in to the 'parallel' step so we can fire all the builds at once
                        builders["${image}-${env}"] = {
                            node('docker') {
                                /* Requires the Docker Pipeline plugin to be installed */
                                docker.image("ikus060/docker-debian-py2-py3:${image}").inside {
                                    stage("${image}-${env}:Initialize") {
                                        // Wipe working directory to make sure to build clean.
                                        deleteDir()
                                         // Checkout 
                                        checkout scm
                                        echo 'Upgrade python and install dependencies to avoid compiling from sources.'
                                        sh 'apt-get update && apt-get -qq install python-pysqlite2 libldap2-dev libsasl2-dev rdiff-backup node-less'
                                        sh 'pip install pip setuptools tox --upgrade'
                                    }
                                    stage("${image}-${env}:Build") {
                                        echo 'Compile catalog and less'
                                        sh 'python setup.py build'
                                    }
                                    stage("${image}-${env}:Test") {
                                        try {
                                            sh "tox --recreate --workdir /tmp --sitepackages -e ${env}"
                                        } finally {
                                            junit "nosetests-${env}.xml"
                                            stash includes: "coverage-${env}.xml", name: 'coverage'
                                        }
                                    }
                                }
                            }
                        }
                    }}}
                    
                    parallel builders
                }
            }
        }
        stage ('Publish Coverage') {
            steps {
                unstach 'coverage'
                script {
                    step([$class: 'CoberturaPublisher', coberturaReportFile: "coverage-*.xml"])
                }
            }
        }
        stage ('Release') {
            when {
                environment name: 'Release', value: 'true'
            }
            steps {
                script {
                    version = sh(
                        script: 'python setup.py --version | tail -n1',
                        returnStdout: true
                    ).trim().replaceFirst(".dev.*", ".${BUILD_NUMBER}")
                }
                sh 'git checkout .'
                // Change version.
                sh """
                    sed -i.bak -r "s/version='(.*).dev.*'/version='${version}'/" setup.py
                """
                // Create Tag in git repo.
                sh """
                    git config --local user.email "jenkins@patrikdufresne.com"
                    git config --local user.name "Jenkins"
                    git tag 'v${version}'
                    export REPO=`git config remote.origin.url`
                    git push http://${GITLAB}@\044{REPO#*//} --tags
                """
                addInfoBadge "v${version}"
            }
        }
        stage('Upload') {
            steps {
                // Upload packages to kalo
                sshagent (credentials: ['www-data-kalo']) {
                    sh "scp -o StrictHostKeyChecking=no scp dist/*.tar.gz dist/*.whl www-data@kalo.patrikdufresne.com:/var/www/patrikdufresne/archive/rdiffweb"
                }
            }
        }
        stage('Promote') {
            when {
                environment name: 'Release', value: 'true'
                environment name: 'Promote', value: 'true'
            }
            steps {
                sh """cat > ~/.pypirc << EOF
[distutils]
index-servers =
  pypi

[pypi]
username=${PYPI_USR}
password=${PYPI_PSW}   
EOF
"""
                sh 'pip install wheel --upgrade'
                sh 'python setup.py sdist bdist_wheel upload -r pypi'
            }
        }
        stage('GitHubPush') {
            steps { 
                sh "git push --force https://${GITHUB}@github.com/ikus060/rdiffweb.git refs/remotes/origin/${BRANCH_NAME}:refs/heads/${BRANCH_NAME}"
                sh "git push https://${GITHUB}@github.com/ikus060/rdiffweb.git --tags"
            }
        }
    }
}
