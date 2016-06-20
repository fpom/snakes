all:
	@echo "Commands:"
	@echo "  release    prepare source for release"
	@echo "  tgz        build a source tarball"
	@echo "  dput       build and upload Ubuntu packages"
	@echo "  clean      delete some garbage files"
	@echo "  test       run tests through supported Python implementations"
	@echo "  next-deb   increments debian/VERSION"
	@echo "  next-ppa   increments debian/PPA"
	@echo "  lang       build generated files in snakes/lang"
	@echo "  emacs      compile Emacs files"
	@echo "  pip        upload to PyPI"

committed:
	hg summary|grep -q '^commit: (clean)$$'

pip: utils/abcd-mode.el
	python setup.py sdist upload

next-deb:
	echo 1 > debian/PPA
	echo $$((1+$$(cat debian/VERSION))) > debian/VERSION

utils/abcd-mode.elc: utils/abcd-mode.el
	emacs -batch -f batch-byte-compile utils/abcd-mode.el

next-ppa:
	echo $$((1+$$(cat debian/PPA))) > debian/PPA

release: committed tgz
	hg tag version-$$(cat VERSION)
	echo 1 > debian/PPA
	echo 1 > debian/VERSION
	hg commit -m "version $$(cat VERSION)"
	hg push

lang:
	python mklang.py

tgz: committed
	hg archive snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	tar cf snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	rm -rf snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	gzip -9 snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar
	gpg --armor --sign --detach-sig snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar.gz

dput.sh: VERSION debian/*
	python mkdeb.py

dput: committed dput.sh
	sh dput.sh

clean:
	rm -f $$(find . -name ",*")
	rm -f $$(find . -name "*.pyc")
	rm -f $$(find . -name "*~")
	rm -f $$(find . -name "*.class")
	rm -rf $$(find . -type d -name __pycache__)

test:
	python2.5 test.py
	python2.6 test.py
	python2.7 test.py
	python3 test.py
	unladen test.py
	pypy test.py
	spypy test.py
	stackless test.py
	jython test.py
