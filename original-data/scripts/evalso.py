#!/usr/bin/env python

from __future__ import with_statement

'''
Evaluate standoff-formatted data against gold standard annotations.

Author:     Sampo Pyysalo <sampo pyysalo gmail com>
Version:    2013-10-15
'''

import sys
import re
import os
import optparse

from os.path import basename, splitext

# global
options = None

def optparser():
    op = optparse.OptionParser("\n  %prog [OPTIONS] GOLD TEST\n\nDescription:\n  evaluates tagging against gold")
    op.add_option("-s","--suffix", default="ann",
                  help="Suffix of annotated files.")
    op.add_option("-e","--exact", action="store_true", default=False,
                  help="Require exact match (default).")
    op.add_option("-o","--overlap", action="store_true", default=False,
                  help="Treat any overlap between entities as a match.")
    op.add_option("-l","--leftboundary", action="store_true", default=False,
                  help="Only require left boundary to match.")
    op.add_option("-r","--rightboundary", action="store_true", default=False,
                  help="Only require right boundary to match.")
    op.add_option("-i","--ignoretype", action="store_true", dest="notype",
                  default=False,help="Ignore types.")
    op.add_option("-m","--allowmissing", action="store_true", default=False,
                  help="Allow gold files lacking a corresponding test file.")
    op.add_option("-f","--filtertypes", default=[],
                  help="Remove given types from input.")
    op.add_option("-d","--docids", action="store_true", default=False,
                  help="Include document IDs in verbose output (with -v).")
    op.add_option("-F","--force", action="store_true", default=False,
                  help="Force evaluation even if there are errors.")
    op.add_option("-v","--verbose", action="store_true", default=False,
                  help="Verbose output.")
    return op

class Span(object):
    """
    Represents an annotated span of text with a type.
    """
    def __init__(self, id_, type_, start, end, text):
        self.id_ = id_
        self.type_ = type_
        self.start = start
        self.end = end
        self.text = text

        self.matched = False
        self.matching = {}

    def clear_matched(self):
        self.matched = False
        self.matching = {}

    def mark_matching(self, other):
        self.matched = True
        self.matching[other] = True

    def __str__(self):
        return "%s\t%s %s %s\t%s" % (self.id_, self.type_, 
                                     self.start, self.end, self.text)

# parses a standoff-formatted file containing tagged entities.
# returns a dictionary indexed with entity ids containing 
# (type, start, end, text) tuples.
def parse_standoff(fn):
    global options

    with open(fn, 'rU') as f:
        tagged = {}
        flags = {}
        for l in f:
            l = l.strip()

            mt = re.match(r'^(T\S+)\t(\S+) (\d+) (\d+)\t(.*)$', l)
            ma = re.match(r'^([MA]\S+)\t(\S+) (\S+)$', l)
            if mt:
                # textbound
                id_, type_, start, end, text = mt.groups()
                start, end = int(start), int(end)

                if type_ in options.filtertypes:
                    if options.verbose:
                        print >> sys.stderr, "Note: filtering out: %s" % l
                    continue

                assert id_ not in tagged, "ERROR: dup id %s" % id_
                tagged[id_] = Span(id_, type_, start, end, text)

            elif ma:
                # attribute
                aid, atype, id_ = ma.groups()
                if id_ not in flags:
                    flags[id_] = {}
                assert atype not in flags[id_], "ERROR: dup attrib"
                flags[id_][atype] = True
            else:
                # just check format sanity
                if re.match(r'^#', l):
                    # comment
                    continue
                elif re.match(r'^[RN]', l):
                    # relation/normalization
                    continue
                elif re.match(r'^\*', l):
                    # equiv
                    continue
                assert False, "ERROR: failed to parse line in %s: '%s'" % (fn, l)

    return tagged, flags

def match(gtype, gstart, gend, gtext, ttype, tstart, tend, ttext):
    global options

    if gtype != ttype and not options.notype:
        # type mismatch
        return False

    if gstart == tstart and gend == tend:
        # straight full match
        if gtext != ttext:
            print >> sys.stderr, "ERROR: span match with different texts: '%s' (gold) vs '%s' (test)" % (gtext, ttext)
            if not options.force:
                assert False, 'Fatal: text mismatch'
        return True

#    if options.overlap and (tend > gstart and tstart < gend):
    if options.overlap and ((gstart >= tstart and gstart < tend) or
                            (tstart >= gstart and tstart < gend)):
        if options.verbose:
            print >> sys.stderr, "OVERLAP MATCH: %d-%d : %d-%d ('%s' vs '%s')" % (gstart, gend, tstart, tend, gtext, ttext)
        return True

    elif options.leftboundary and gstart == tstart:
        if options.verbose:
            print >> sys.stderr, "LEFT-B MATCH: %d-%d : %d-%d ('%s' vs '%s')" % (gstart, gend, tstart, tend, gtext, ttext)
        return True

    elif options.rightboundary and gend == tend:
        if options.verbose:
            print >> sys.stderr, "RIGHT-B MATCH: %d-%d : %d-%d ('%s' vs '%s')" % (gstart, gend, tstart, tend, gtext, ttext)
        return True

    return False

def tf_counts(gold, test):
    global options

    # Note: TP calculated separately for gold and predicted to allow
    # for approximate matching where a single prediction can match
    # several things in gold (and vice versa).

    TPg, TPt, FP, FN = 0, 0, 0, 0
    for g in gold.values():
        if g.matched:
            TPg += 1
        else:
            FN += 1

    for t in test.values():
        if t.matched:
            TPt += 1
        else:
            FP += 1

    return TPg, TPt, FP, FN

def print_tf(gold, test, docid, goldtp=False):
    for g in gold.values():
        if options.docids:
            print >> sys.stderr,"%s" % docid,             
        if not g.matched:            
            print >> sys.stderr, "FN: %s" % g
        elif goldtp:
            print >> sys.stderr, "TP: %s" % g
    for t in test.values():
        if options.docids:
            print >> sys.stderr, "%s" % docid,             
        if not t.matched:
            print >> sys.stderr, "FP: %s" % t
        elif not goldtp:
            print >> sys.stderr, "TP: %s" % t

def leftmost_longest(a,b):
    # sort comparator for Span objects
    if a.start < b.start:
        return -1
    elif a.start > b.start:
        return 1
    else:
        return cmp(b.end, a.end)

def mark_matched(gold, test):
    # clear possible previous "matching" markings
    for e in gold.values():
        e.clear_matched()
    for e in test.values():
        e.clear_matched()

    # sort both for traversal
    gold_sorted = sorted(gold.values(), leftmost_longest)
    test_sorted = sorted(test.values(), leftmost_longest)

    # traverse annotations in order, keep track of "open" ones for
    # determining matches
    gold_open, test_open = [], []
    gold_idx, test_idx = 0, 0
    while True:
        have_gold = gold_idx < len(gold_sorted)
        have_test = test_idx < len(test_sorted)
        
        # identify next annotation
        picked_gold = None
        if have_gold and have_test:
            if gold_sorted[gold_idx].start < test_sorted[test_idx].start:
                next_open = gold_sorted[gold_idx]
                picked_gold = True
            else:
                next_open = test_sorted[test_idx]
                picked_gold = False
        elif have_gold:
            next_open = gold_sorted[gold_idx]
            picked_gold = True
        elif have_test:
            next_open = test_sorted[test_idx]
            picked_gold = False
        else:
            # all over, we're done
            break

        # determine which annotations remain open when moving to the
        # next one
        gold_open = [e for e in gold_open if e.end > next_open.start]
        test_open = [e for e in test_open if e.end > next_open.start]

        # make the move
        if picked_gold:
            gold_open.append(next_open)
            gold_idx += 1
        else:
            test_open.append(next_open)
            test_idx += 1

        for g in gold_open:
            for t in test_open:
                if match(g.type_, g.start, g.end, g.text,
                         t.type_, t.start, t.end, t.text):
                    g.mark_matching(t)
                    t.mark_matching(g)

    return True

def prec_rec_F(TPg, TPt, FP, FN):
    if TPt + FP == 0:
        p = 0.0
    else:
        p = 100.0 * TPt / (TPt + FP)
    if TPg + FN == 0:
        r = 0
    else:
        r = 100.0 * TPg / (TPg + FN)
    if p+r == 0:
        F = 0.0
    else:
        F = 2*p*r/(p+r)

    return p, r, F

def report(TPg, TPt, FP, FN, header=None, out=sys.stdout):
    p, r, F = prec_rec_F(TPg, TPt, FP, FN)
    if header is not None:
        out.write(header)
    print >> out, "precision %.2f%% (%d/%d) recall %.2f%% (%d/%d) F %.2f%%" % \
        (p, TPt, TPt+FP, r, TPg, TPg+FN, F)

def process(goldfn, testfn):
    global options

    gold, gold_flags = parse_standoff(goldfn)
    test, test_flags = parse_standoff(testfn)

    mark_matched(gold, test)
    
    TPg, TPt, FP, FN = tf_counts(gold, test)
    if options.verbose:
        print_tf(gold, test, splitext(basename(goldfn))[0])
    report(TPg, TPt, FP, FN)

def process_dir(golddir, testdir):
    global options

    gold_files = os.listdir(golddir)
    test_files = os.listdir(testdir)

    # filter to those with the correct suffix
    gold_files = [f for f in gold_files if f.split(".")[-1] == options.suffix]
    test_files = [f for f in test_files if f.split(".")[-1] == options.suffix]
    
    # add directory
    gold_files = [os.path.join(golddir, f) for f in gold_files]
    test_files = [os.path.join(testdir, f) for f in test_files]    
    
    # quick reference
    in_test = {}
    for f in test_files:
        in_test[os.path.basename(f)] = f

    # check for missing files
    missing_gold = set()
    for goldfn in gold_files:
        gb = os.path.basename(goldfn)
        if gb not in in_test:
            missing_gold.add(gb)
    if missing_gold and not options.allowmissing:
        print >> sys.stderr, "Error: missing test labels for gold files %s" % " ".join(missing_gold)
        print >> sys.stderr, "Exiting: missing %d files." % len(missing_gold)
        return -1
    if missing_gold:
        assert options.allowmissing, "INTERNAL ERROR"
        # ignore missing part
        if options.verbose:
            print >> sys.stderr, "Ignoring %d missing files" % len(missing_gold)
        gold_files = [g for g in gold_files 
                      if os.path.basename(g) not in missing_gold]

    # take totals
    total_TPg, total_TPt, total_FP, total_FN = 0, 0, 0, 0

    # and per-type stats
    TPg_by_type, TPt_by_type, FP_by_type, FN_by_type = {}, {}, {}, {}
    all_gold_types = {}
    all_test_types = {}

    # and per-flag stats
    TPg_by_flag, TPt_by_flag, FP_by_flag, FN_by_flag = {}, {}, {}, {}
    all_gold_flags = {}
    all_test_flags = {}

    for goldfn in gold_files:
        gb = os.path.basename(goldfn)

        assert gb in in_test, "Error: missing test labels for gold file %s" % gb

        testfn = in_test[gb]

        gold, gold_flag = parse_standoff(goldfn)
        test, test_flag = parse_standoff(testfn)

        mark_matched(gold, test)
        TPg, TPt, FP, FN = tf_counts(gold, test)

        if options.verbose:
            print_tf(gold, test, splitext(basename(goldfn))[0])
            report(TPg, TPt, FP, FN)

        total_TPg += TPg
        total_TPt += TPt
        total_FP += FP
        total_FN += FN

        # repeat evaluation separately for each type
        gold_types = dict(map(lambda a:(a,True), [g.type_ 
                                                  for g in gold.values()]))
        test_types = dict(map(lambda a:(a,True), [t.type_ 
                                                  for t in test.values()]))

        for t in gold_types:
            all_gold_types[t] = True
        for t in test_types:
            all_test_types[t] = True

        all_types = dict(map(lambda a:(a,True), gold_types.keys()+test_types.keys()))

        for d in TPg_by_type, TPt_by_type, FP_by_type, FN_by_type:
            for t in all_types:
                d[t] = d.get(t,0)

        for t in all_types:
            # filter sets involving the relevant type
            if t not in gold_types:
                type_gold = gold
            else:
                type_gold = {}
                for eid in gold:
                    if gold[eid].type_ == t:
                        type_gold[eid] = gold[eid]

            if t not in test_types:
                type_test = test
            else:
                type_test = {}
                for eid in test:
                    if test[eid].type_ == t:
                        type_test[eid] = test[eid]

            mark_matched(type_gold, type_test)
            #gold_matched, test_matched = get_matched(type_gold, type_test)
            TPg, TPt, FP, FN = tf_counts(type_gold, type_test)

            TPg_by_type[t] += TPg
            TPt_by_type[t] += TPt
            FP_by_type[t] += FP
            FN_by_type[t] += FN

        # repeat evaluation separately for each flag
        gold_flags = {}
        for eid in gold_flag:
            for f in gold_flag[eid]:
                gold_flags[f] = True
        test_flags = {}
        for eid in test_flag:
            for f in test_flag[eid]:
                test_flags[f] = True
        all_flags = dict(map(lambda a:(a,True), gold_flags.keys()+test_flags.keys()))

        for f in gold_flags:
            all_gold_flags[f] = True
        for f in test_flags:
            all_test_flags[f] = True

        for d in TPg_by_flag, TPt_by_flag, FP_by_flag, FN_by_flag:
            for f in all_flags:
                d[f] = d.get(f,0)

        for f in all_flags:
            # filter sets involving the relevant type
            if f not in gold_flags:
                flag_gold = gold
            else:
                flag_gold = {}
                for eid in gold:
                    if eid in gold_flag and f in gold_flag[eid]:
                        flag_gold[eid] = gold[eid]

            if f not in test_flags:
                flag_test = test
            else:
                flag_test = {}
                for eid in test:
                    if eid in test_flag and f in test_flag[eid]:
                        flag_test[eid] = test[eid]

            mark_matched(flag_gold, flag_test)
            #gold_matched, test_matched = get_matched(flag_gold, flag_test)
            TPg, TPt, FP, FN = tf_counts(flag_gold, flag_test)

            TPg_by_flag[f] += TPg
            TPt_by_flag[f] += TPt
            FP_by_flag[f] += FP
            FN_by_flag[f] += FN

        # finally, mark "used"
        in_test[gb] = None

    # print by-flag
    for f in sorted(all_gold_flags):
        report(TPg_by_flag[f], TPt_by_flag[f], FP_by_flag[f], FN_by_flag[f],
               "FLAG: %25s " % f)
    for f in sorted(all_test_flags):
        if f in all_gold_flags:
            continue # no dups
        report(TPg_by_flag[f], TPt_by_flag[f], FP_by_flag[f], FN_by_flag[f],
               "FLAG: %25s " % f)

    # print by-type (unless types are being ignored)
    if not options.notype:
        for t in sorted(all_gold_types):
            report(TPg_by_type[t], TPt_by_type[t], FP_by_type[t], FN_by_type[t],
                   "TYPE: %25s " % t)
        for t in sorted(all_test_types):
            if t in all_gold_types:
                continue # no dups
            report(TPg_by_type[t], TPt_by_type[t], FP_by_type[t], FN_by_type[t],
                   "TYPE: %25s " % t)

    # print totals
    report(total_TPg, total_TPt, total_FP, total_FN, "TOTAL:\n")

    # sanity
    test_extras = [b for b in in_test if in_test[b] is not None]
    if len(test_extras) != 0:
        print >> sys.stderr, "Warning: extra files in test: %s" % ", ".join(test_extras)

    # sanity
    test_only_types = [t for t in all_test_types if t not in all_gold_types]
    if test_only_types and not options.notype:
        print >> sys.stderr, "Warning: types only appearing in test data: %s" % " ".join(test_only_types)

def main(argv):
    global options
    options, args = optparser().parse_args()

    if len(args) != 2:
        optparser().print_usage()
        return 1

    # argument sanity
    criterion_count = sum([1 if a else 0 for a in \
                               (options.exact, options.overlap, 
                                options.leftboundary, options.rightboundary)])
    if criterion_count > 1:
        print >> sys.stderr, "Please specify at most one of the 'exact', 'overlap', 'leftboundary' and 'rightboundary' options"
        return 1
    elif criterion_count == 0:
        options.exact = True # default

    # argument preparation
    if options.filtertypes != []:
        options.filtertypes = options.filtertypes.split(",")
        
    goldfn, testfn = args

    if os.path.isdir(goldfn) and os.path.isdir(testfn):
        process_dir(goldfn, testfn)
    elif not os.path.isdir(goldfn) and not os.path.isdir(testfn):
        process(goldfn, testfn)
    else:
        print >> sys.stderr, "Error: one of arguments is directory, other file"
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
