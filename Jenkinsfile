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
            parallel {
                stage('Test on Python2.7') {
                    agent {
                        docker {
                            image 'ikus060/docker-debian-py2-py3:jessie'
                        }
                    }
                    steps {
                        sh 'apt-get update && apt-get -qq install python-pysqlite2 libldap2-dev libsasl2-dev rdiff-backup node-less'
                        sh 'pip install pip setuptools tox --upgrade'
                        sh """
                            export TOXENV=`tox --listenvs | grep py27 | tr '\n' ','`
                            tox --recreate --workdir /tmp --sitepackages
                        """
                    }
                    post {
                        success {
                            junit "nosetests-*.xml"
                            stash includes: 'coverage-*.xml', name: 'coverage'
                        }
                    }
                }
                stage('Test on Python3.4') {
                    agent {
                        docker {
                            image 'ikus060/docker-debian-py2-py3:jessie'
                        }
                    }
                    steps {
                        sh 'apt-get update && apt-get -qq install python-pysqlite2 libldap2-dev libsasl2-dev rdiff-backup node-less'
                        sh 'pip install pip setuptools tox --upgrade'
                        sh """
                            export TOXENV=`tox --listenvs | grep py27 | tr '\n' ','`
                            tox --recreate --workdir /tmp --sitepackages
                        """
                    }
                    post {
                        success {
                            junit "nosetests-*.xml"
                            stash includes: 'coverage-*.xml', name: 'coverage'
                        }
                    }
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
