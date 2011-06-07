import os, os.path

snakes_version = open("VERSION").readline().strip()
package_version = open("debian/VERSION").readline().strip()
ppa_version = open("debian/PPA").readline().strip()
changelog_version = open("debian/changelog").readline().split()[1].strip("()")
distribs = [l.strip().split()[0] for l in open("debian/DISTRIB")]
base_dir = os.getcwd()
base_dist_dir = "dist"
dput_sh = open("dput.sh", "w")

def system (command) :
    print("*** %s" % command)
    retcode = os.system(command)
    if retcode != 0 :
        print("*** error return status (%s)" % retcode)
        sys.exit(retcode)

def chdir (path) :
    print("*** cd %s" % path)
    os.chdir(path)

def changelog (path, dist) :
    full_version = "%s-%s~ppa%s~%s1" % (snakes_version, package_version,
                                        ppa_version, dist)
    chdir(path)
    system("debchange -b --newversion %s --distribution %s 'see NEWS'"
           % (full_version, dist))
    chdir(base_dir)

def build_package (dist_dir, dist) :
    full_version = "%s-%s~ppa%s~%s1" % (snakes_version, package_version,
                                        ppa_version, dist)
    deb_dir = os.path.join(dist_dir, "python-snakes_%s" % full_version)
    if not os.path.isdir(dist_dir) :
        print("*** make dir %r" % dist_dir)
        os.makedirs(dist_dir)
    if os.path.isdir(deb_dir) :
        system("rm -rf %s" % deb_dir)
    system("hg archive %s" % deb_dir)
    changelog(deb_dir, dist)
    system("sed -i -e 's/DATE/$(date -R)/' %s/debian/copyright" % deb_dir)
    system("sed -i -e 's/UNRELEASED/%s/' %s/debian/changelog" % (dist, deb_dir))
    chdir(deb_dir)
    system("make doc")
    system("dpkg-buildpackage")
    system("dpkg-buildpackage -S -sa")
    chdir(base_dir)
    dput_sh.write("dput lp %s_source.changes\n" % deb_dir)

main_version = "%s-%s" % (snakes_version, package_version)
if main_version != changelog_version :
    system("debchange --newversion %s --distribution UNRELEASED 'see NEWS'"
           % main_version)
    system("hg commit -m 'updated debian/changelog' debian/changelog")

for dist in distribs :
    build_package(base_dist_dir, dist)
dput_sh.close()
