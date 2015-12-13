#!/bin/bash

# Partition files in input directory according to lists of file names.

set -u
set -e

USAGESTR="Usage: $0 INDIR OUTDIR LIST [LIST [...]]"

if [ $# -lt 3 ]; then
    echo $USAGESTR
    exit 1
fi

INDIR=$1
shift

if [ ! -d $INDIR ]; then
    echo "$INDIR is not a directory"
    echo $USAGESTR
    exit 1
fi

OUTDIR=$1
shift

if [ ! -d $OUTDIR ]; then
    echo "$OUTDIR is not a directory"
    echo $USAGESTR
    exit 1
fi

for f in $@; do
    if [ ! -f $f ]; then
	echo "$f is not a file"
	echo $USAGESTR
	exit 1
    fi
done

# sanity checks

dups=0
while read -r l; do
    echo "duplicate line:" `echo "$l" | perl -pe 's/^\s*\d+\s*//'` >&2
    dups=1
done < <(cat $@ | sort | uniq -c | egrep -v '^[[:space:]]*1[[:space:]]')

if [ "$dups" -ne 0 ]; then
    echo "not a partition: lists overlap: $@"
    exit 1
fi

miss=0
while read -r l; do
    echo "not found in $INDIR: $l" >&2
    miss=1
done < <(comm -2 -3 <(cat $@ | sort) <(ls $INDIR | perl -pe 's/(.*)\..*/$1/' | sort))

if [ "$miss" -ne 0 ]; then
    echo "error: files missing from $INDIR"
    exit 1
fi

extra=0
while read -r l; do
    echo "not in lists: $l" >&2
    extra=1
done < <(comm -1 -3 <(cat $@ | sort) <(ls $INDIR | perl -pe 's/(.*)\..*/$1/' | sort | uniq))

if [ "$extra" -ne 0 ]; then
    echo "error: extra files in $INDIR"
    exit 1
fi

for s in $@; do
    o=$OUTDIR/`basename $s .list | perl -pe 's/-doc(ument)?s$//'`
    if [ -e "$o" ]; then
	echo "error: $o (for $s) exists, not overwriting"
	exit 1
    fi
done

# process

for s in $@; do
    o=$OUTDIR/`basename $s .list | perl -pe 's/-doc(ument)?s$//'`
    mkdir "$o"
    for n in `cat $s`; do
	cp $INDIR/$n.* "$o"
    done
done

# output stats

for s in $@; do
    o=`basename $s .list | perl -pe 's/-doc(ument)?s$//'`
    echo "$o:" `ls $OUTDIR/$o | wc -l` "files ("`ls $OUTDIR/$o | perl -pe 's/.*\././' | sort | uniq -c`")" >&2
done
