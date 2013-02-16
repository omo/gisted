
PIP_REQUIREMENT = "requirements.txt"
TEST_OPTIONS    = ""

run:
	. ./bin/activate && python web.py
grun:
	. ./bin/activate && gunicorn --config=confs/gunicorn.conf.py web:app
test:
	. ./bin/activate && python -m unittest discover ${TEST_OPTIONS}

upload-lessig:
	./bin/gisteder upload --url "http://lessig.tumblr.com/post/24065401182/commencement-address-to-atlantas-john-marshall-law" --title "Commencement Address to Atlanta’s John Marshall Law School" --file data/lessig.md

download-hello:
	./bin/gisteder download --gist 4965816
#
# virtualenv related rules
#
freeze: ${PIP_REQUIREMENT}

${PIP_REQUIREMENT}:
	. ./bin/activate && pip freeze > $@

.PHONY: ${PIP_REQUIREMENT} deploy run clean test
