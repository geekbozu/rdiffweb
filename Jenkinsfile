def axisImages = ['jessie']
def axisPython = ['py27', 'py3']
//def axisCherrypy = ['cherrypy35','cherrypy4','cherrypy5','cherrypy6','cherrypy7','cherrypy8','cherrypy9','cherrypy10','cherrypy11','cherrypy12']
def axisCherrypy = ['cherrypy11','cherrypy12']

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
        node {
            /* Requires the Docker Pipeline plugin to be installed */
            docker.image("ikus060/docker-debian-py2-py3:${image}").inside {
                stage("Initialize") {
                    echo 'Enforce timezone for tests to work.'
                    sh 'ln -snf /usr/share/zoneinfo/America/Montreal /etc/localtime && echo "America/Montreal" > /etc/timezone'
                    echo 'Upgrade python and install dependencies to avoid compiling from sources.'
                    sh 'apt-get update && apt-get -qq install python-pysqlite2 libldap2-dev libsasl2-dev rdiff-backup'
                    sh 'pip install pip setuptools tox --upgrade'
                    echo 'Compile catalog to make the test pass'
                    sh 'python setup.py compile_all_catalogs'
                }
                stage("Test") {
                    try {
                        sh "tox --recreate --workdir /tmp --sitepackages -e ${env}"
                    } finally {
                        junit "nosetests-${env}.xml"
                    }
                }
            }
        }
    }
}}}

node {
    stage ('Checkout') {
        // Wipe working directory to make sure to build clean.
        deleteDir()
        // Checkout 
        checkout scm
        // Make sure to checkout the branch to properly push tag in other steps.
        sh '''
            git config --local user.email "jenkins@patrikdufresne.com"
            git config --local user.name "Jenkins"
        '''        
    }

    parallel builders
    
    stage ('Publish') {
        // Define version
        def pyVersion = sh(
          script: 'python setup.py --version | tail -n1',
          returnStdout: true
        ).trim()
        def version = pyVersion.replaceFirst(".dev.*", ".dev${BUILD_NUMBER}")
        if (env.BRANCH_NAME == 'master') {
            version = pyVersion.replaceFirst(".dev.*", ".${BUILD_NUMBER}")
        }
        
        // Push changes to git
        withCredentials([usernamePassword(credentialsId: 'gitlab-jenkins', usernameVariable: 'GIT_USERNAME', passwordVariable: 'GIT_PASSWORD')]) {
            sh """
              sed -i.bak -r "s/version='(.*).dev.*'/version='${version}'/" setup.py
              git commit setup.py -m 'Release ${version}'
              git tag '${version}'
              git push http://${GIT_USERNAME}:${GIT_PASSWORD}@git.patrikdufresne.com/pdsl/rdiffweb.git --tags
            """
        }
        
        // Publish to pypi
        docker.image("ikus060/docker-debian-py2-py3:jessie").inside {
            withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'ikus060-pypi', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD']]) {
                sh 'pip install wheel --upgrade'
                sh 'python setup.py sdist bdist_wheel upload -r https://${USERNAME}:${PASSWORD}@testpypi.python.org/pypi'
            }
        }
        
    }
}