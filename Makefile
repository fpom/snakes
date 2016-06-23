all:
	@echo "Commands:"
	@echo "  clean      delete some garbage files"
	@echo "  nextver    increments version number"
	@echo "  test       run tests through supported Python implementations"
	@echo "  lang       build generated files in snakes/lang"
	@echo "  emacs      compile Emacs files"
	@echo "  pip        upload to PyPI"

nextver:
	python version.py next

version:
	python version.py check

pip: emacs version
	python setup.py sdist upload

emacs: utils/abcd-mode.elc

utils/abcd-mode.elc: utils/abcd-mode.el
	emacs -batch -f batch-byte-compile utils/abcd-mode.el

lang:
	python mklang.py

clean:
	rm -f $$(find . -name ",*")
	rm -f $$(find . -name "*.pyc")
	rm -f $$(find . -name "*~")
	rm -f $$(find . -name "*.class")
	rm -rf $$(find . -type d -name __pycache__)

test:
	python2.5 test.py
	python2.7 test.py
	python3 test.py
	unladen test.py
	pypy test.py
	jython test.py
