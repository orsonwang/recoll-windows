#!/bin/sh

# MUST run from the directory where the build happens (distrohome/deb11 or ~/appimage-build on the VM

# Note: this supposes that all used python version have been built
# from source and installed with make altinstall, and that a
# py3versions program is found in the PATH before the system one, and
# outputs the desired versions. E.g.:
# #!/bin/sh
# echo 3.8 3.9 3.10 3.11 3.12 3.13

fatal()
{
    echo $*
    exit 1
}

BUILDTOP=`pwd`
RCLDISTS=/home/dockes/projets/fulltext/web-recoll
RCLSRC=/home/dockes/projets/fulltext/recoll

FROMGIT=0
RECOLL_VERSION=1.43.14

UNRTF=unrtf-0.21.11
ANTIWORD=antiword

DEPLOYBINDIR=~/.local/bin

APPDIR=$BUILDTOP/AppDir/
BUILDDIR=$BUILDTOP/recoll-build
# NOTE: delete the builddir when changing versions. Not done automatically because complicated
#rm -rf $BUILDDIR

if test $FROMGIT -ne 0; then
    RECOLL=/home/dockes/projets/fulltext/recoll/src
else
    # TBD: Replace this with curl or wget from the web site so we don't need a local copy on the VM ?
    RECOLL=$BUILDTOP/recoll-${RECOLL_VERSION}
    test -d $RECOLL || (cd $BUILDTOP && tar xf $RCLDISTS/recoll-${RECOLL_VERSION}.tar.gz) || \
        fatal source extraction
fi

auxprogs()
{
    # This works because:
    # - We change the apps to find their resources relative to the exec. Ok for antiword and unrtf
    # - We make sure that the PATH is ok for the handlers to find them in the mounted bin
    cd  || exit 1
    
    echo "Building UNRTF"
    cd $BUILDTOP/$UNRTF || exit 1
    ./configure --prefix=/usr
    make -j 4 || exit 1
    make install DESTDIR=$APPDIR || exit 1

    echo "Building ANTIWORD"
    cd $BUILDTOP/$ANTIWORD
    make -f Makefile.Linux
    cp antiword $APPDIR/usr/bin/ || exit 1
    mkdir -p $APPDIR/usr/share/antiword || exit 1
    cp -rp Resources/*.txt Resources/fontnames $APPDIR/usr/share/antiword/ || exit 1
}

rm -rf ${APPDIR}/*

cd $RECOLL/

if test $FROMGIT -ne 0; then
    hash=`git log -n 1 | head -1 | awk '{print $2}' | cut -b 1-8`
fi
RECOLL_VERSION=`cat RECOLL-VERSION.txt`

# The -Dappimage=true is not used after 2025-11-20, but needed for recoll-1.43.7
meson setup --prefix=/usr ${BUILDDIR}
ninja -C ${BUILDDIR}

echo;echo INSTALLING TO $APPDIR
DESTDIR=$APPDIR ninja -C ${BUILDDIR} install || exit 1

echo;echo ALSO INSTALLING TO /usr FOR PYTHON BUILDS
sudo ninja -C ${BUILDDIR} install || exit 1

echo Copying Python binary extension shared objects
cp ${BUILDDIR}/python/recoll/*.so $APPDIR/usr/lib/python3/dist-packages/recoll || exit 1
cp ${BUILDDIR}/python/pychm/*.so $APPDIR/usr/lib/python3/dist-packages/recollchm || exit 1
cp ${BUILDDIR}/python/pyaspell/*.so $APPDIR/usr/lib/python3/dist-packages/ || exit 1

auxprogs

cd $BUILDTOP
$DEPLOYBINDIR/linuxdeploy-x86_64.AppImage \
    --appdir $APPDIR \
    --custom-apprun=$RCLSRC/packaging/appimage/AppRun \
    --plugin qt --output appimage
                                          
dte=`date +%Y%m%d`
mv Recoll-x86_64.AppImage Recoll-${RECOLL_VERSION}-${dte}-${hash}-x86_64.AppImage
