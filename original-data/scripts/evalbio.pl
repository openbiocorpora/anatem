#!/usr/bin/perl
require 5.000;

use Getopt::Std;
getopts('ha:r:l:es1');

$afield = -1;
$rfield = -1;

@objs=(
    "Anatomical_system",
    "Cancer",
    "Cell",
    "Cellular_component",
    "Developing_anatomical_structure",
    "Immaterial_anatomical_entity",
    "Multi-tissue_structure",
    "Organ",
    "Organism_subdivision",
    "Organism_substance",
    "Pathological_formation",
    "Tissue",
    );
$alls="[-ALL-]";

if ($opt_1) {
    # single non-specific class
    @objs = ("");
}

# for quick ref
my %knowncls = map { $_ => 1 } @objs;

if (($opt_h) || ($#ARGV != 1)) {
    die "\n" .
	"[eval] 2004.10.14 Jin-Dong Kim (jdkim\@is.s.u-tokyo.ac.jp)\n" .
	"       (variant for AnatEM evaluation 2013 Sampo Pyysalo)\n" .
	"\n" .
	"<DESCRIPTION>\n" .
	"\n" .
	"Evaluates the performance of entity mention detection " .
	"by comparing given predictions to given gold data. " .
	"Assumes input files are encoded using the BIO tagging scheme.\n" .
	"\n" .
	"<USAGE>\n" .
	"\n" .
	"evalbio.pl PREDICTIONS GOLD\n" .
	"\n" .
	"<OPTIONS>\n" .
	"\n" .
	"-h               displays this instructions.\n" .
	"-a answer_field  specifies the field with BIO-tags in PREDICTIONS.\n" .
	"                 It is 0-oriented and defaults to -1 (the last field).\n" . 
	"-r refer_field   specifies the field with BIO-tags in the GOLD.\n" .
	"                 It is 0-oriented and defaults to -1 (the last field).\n" . 
# (deprecated)
# 	"-l list_file     specifies the file containing a list of UIDs.\n" .
# 	"                 Only the abstracts of the UIDs will be evaluated.\n" .
# 	"                 If omitted, all the abstracts will be evaluated.\n" .
	"                 Warning: evaluation results may be incoherent for\n" .
	"-s               suppresses input sanity checking, allowing\n" .
	"                 evaluation on (partially) broken data.\n".
	"                 Warning: evaluation results may be incoherent for\n" .
	"                 some broken inputs, use with care.\n" .
	"-1               single-class evaluation, treating all tagged types\n".
	"                 as identical.\n".
	"\n";
} # if

if (defined($opt_a)) {$afield = $opt_a}
if (defined($opt_r)) {$rfield = $opt_r}

open (AFILE, $ARGV[0]) or die "can't open [$ARGV[0]].\n";
open (RFILE, $ARGV[1]) or die "can't open [$ARGV[1]].\n";

if ($opt_l) {
    open (LFILE, $opt_l) or die "can't open [$opt_l].\n";
    while (<LFILE>) {chomp; $abstogo{$_} = 1}
} # if
if (defined($opt_e)) {open (EFILE, ">" . $ARGV[0] . ".chk") or die "can't open [$ARGV[0].chk].\n"}


push @objs, $alls;
foreach $obj (@objs) {
    $nref{$obj} = $nans{$obj} = $nfcrt{$obj} = $nlcrt{$obj} = $nrcrt{$obj} = 0;
}
pop @objs;
@rwrds = @rtags = @atags = @chks = ();
$linenum = 0;

while ($rline = <RFILE>) {
    chomp $rline;

    if ($aline = <AFILE>) {chomp $aline}
    else {die "insufficient predictions.\n"}
    $linenum++;

    if ($rline eq "") {
	if ($aline ne "") {die "sentence alignment error at line $linenum.\n"}

	if ((!$opt_l) || ($abstogo{$medid})) {
	    if (!$opt_s) {
		check_sequence(@rtags);
		check_sequence(@atags);
	    }

	    @rtags = iob2_iobes(@rtags);
	    @atags = iob2_iobes(@atags);	    

	    $match = 0;
	    for ($i=0; $i<=$#rtags; $i++) {

		$rtag = $rtags[$i]; $riob = substr($rtag, 0, 1);
		if ($opt_1) { $rtag = substr($rtag, 0, 1); }
		if (substr($rtag, 1, 1) eq "-") {$rcls = substr($rtag, 2)}
		else {$rcls = ""}

		$atag = $atags[$i]; $aiob = substr($atag, 0, 1);
		if ($opt_1) { $atag = substr($atag, 0, 1); }
		if (substr($atag, 1, 1) eq "-") {$acls = substr($atag, 2)}
		else {$acls = ""}

		if ($rtag eq $atag) {$chks[$i] = ">>>>>TRUE"}
		else {
		    $chks[$i] = ">>>>>FALSE";

		    if ($atag ne "O") {
			if ($rtag eq "O") {$chks[$i] .= "+"}
			elsif ($rtag ne $atag) {$chks[$i] .= "^"}
			else {$chks[$i] .= "@"}
		    } # if
		} # if

		#####
		# object evaluation
		#####
		if (($riob eq "S") || ($riob eq "B")) {$nref{$rcls}++;}
		if (($aiob eq "S") || ($aiob eq "B")) {$nans{$acls}++}

		if ($acls eq $rcls) {
		    if (($aiob eq "S") && ($riob eq "S")) {$nfcrt{$rcls}++; $nlcrt{$rcls}++; $nrcrt{$rcls}++;}
		    if (($aiob eq "S") && ($riob eq "E")) {$nrcrt{$rcls}++}
		    if (($aiob eq "E") && ($riob eq "S")) {$nrcrt{$rcls}++}
		    if (($aiob eq "S") && ($riob eq "B")) {$nlcrt{$rcls}++}
		    if (($aiob eq "B") && ($riob eq "S")) {$nlcrt{$rcls}++}
		    if (($aiob eq "B") && ($riob eq "B")) {$nlcrt{$rcls}++; $match = 1;}
		    if (($aiob eq "E") && ($riob eq "E")) {$nrcrt{$rcls}++; if ($match) {$nfcrt{$rcls}++;}}
		} # if

		if (($atag ne $rtag) || (($aiob ne "B") && ($aiob ne "I"))) {$match = 0}

	    } # for ($i)

	    if (defined($opt_e)) {
		for ($i=0; $i<=$#rtags; $i++) {
		    print EFILE join ("\t", $rwrds[$i], $rtags[$i], $atags[$i], $chks[$i]), "\n";
		} # for
		print EFILE "\n";
	    } # if
	} # if
	@rwrds = @rtags = @atags = @chks = ();
    } # if

    elsif (substr($rline, 0, 11) eq "###MEDLINE:") {
	print EFILE $rline, "\n\n";

	$medid = substr($rline, 11);

	if ($rline = <RFILE>) {chomp $rline}
	else {die "suspicious error at the end of the gold file.\n"}

	if ($aline = <AFILE>) {chomp $aline}
	else {die "suspicious error at the end of the prediction file.\n"}
	$linenum++;

	if (($rline ne "")||($aline ne "")) {die "format mismatch error at the line $linenum.\n"}
    } # if
 

    else {
	@rvals = split(/\t/, $rline);
	push @rwrds, $rvals[$wfield];
	push @rtags, $rvals[$rfield];

	@avals = split(/\t/, $aline);
	push @atags, $avals[$afield];
    } # else
} # while

if (!$opt_s) {
    unless(@rtags == 0 && @atags == 0) {
	die "Error: missing final empty line in input";
    }
}

foreach $obj (@objs) {
    $nref{$alls}+=$nref{$obj}; $nans{$alls}+=$nans{$obj};
    $nfcrt{$alls}+=$nfcrt{$obj}; $nlcrt{$alls}+=$nlcrt{$obj}; $nrcrt{$alls}+=$nrcrt{$obj};
} # foreach

push @objs, $alls;


#####
# Performance Report: Total
#####

$legend = "                                                                                  TP,   FP ( prec. / rec.  / f-score) \n";
$border = "+-------------------------------+-------------------------------------------+-------------------------------------------+-------------------------------------------+\n";
$ctitle = "|                               |               complete match              |             left boundary match           |           right boundary match            |\n";

format PERFROW =
| @||||||||||||||||||||| (@###) | @|||||||||||||||||||||||||||||||||||||||| | @|||||||||||||||||||||||||||||||||||||||| | @|||||||||||||||||||||||||||||||||||||||| |
$obj, $nref{$obj}, &perfs($nref{$obj}, $nans{$obj}, $nfcrt{$obj}), &perfs($nref{$obj}, $nans{$obj}, $nlcrt{$obj}), &perfs($nref{$obj}, $nans{$obj}, $nrcrt{$obj})
.

print $legend, $border, $ctitle, $border;
$~ = "PERFROW";

if ($opt_1) { @objs = ($alls); }

foreach $obj (@objs) {
    write (STDOUT); 
    #print $border;
} # foreach
print $border;

print "\n";


sub perfs {
    my ($numref, $numans, $numcrt) = @_;
    # print STDERR "DEBUG: numref $numref numans $numans numcrt $numcrt numans-numcrt ".($numans-$numcrt)."\n";
    if ($numref==0) {$recall=0} else {$recall=$numcrt/$numref}
    if ($numans==0) {$precision=0} else {$precision=$numcrt/$numans}
    if ($precision+$recall==0) {$fscore = 0} else {$fscore=2*$precision*$recall/($precision+$recall)}

    $recall*=100; $precision*=100; $fscore*=100;
    return sprintf("%4d, %4d (%5.2f\% / %5.2f\% / %5.2f\%)", $numcrt, $numans - $numcrt, $precision, $recall, $fscore);
} # perfs


sub iob2_iobes {
    my (@tags) = @_;
    my ($i);

    for ($i=0; $i<=$#tags; $i++) {

	if (substr($tags[$i], 0, 1) eq "I") {

	    if (($i==$#tags)||(substr($tags[$i+1], 0, 1) ne "I"))
		{substr($tags[$i], 0, 1) = "E"}

	} elsif (substr($tags[$i], 0, 1) eq "B") {

	    if (($i==$#tags)||(substr($tags[$i+1], 0, 1) ne "I"))
		{substr($tags[$i], 0, 1) = "S"}

	} # elsif

    } # for

    return @tags;
} # iob2_iobes

sub check_sequence {
    my (@tags) = @_;

    my $prev_iob = "", $prev_cls = "";
    for ($i=0; $i<=$#tags; $i++) {
	my $tag = $tags[$i];
	my $iob = substr($tag, 0, 1);
	my $cls = "";
	if (substr($tag, 1, 1) eq "-") {
	    $cls = substr($tag, 2);
	    unless ($opt_1 || $knowncls{$cls}) {
		die "Error: unknown class \"$cls\"";
	    }
	}
	if ($opt_1) { $cls = ""; }
	if($iob eq "I" && $prev_iob ne "I" && $prev_iob ne "B") {
	    die "IOB error: \"I\" without preceding \"B\"";
	}
	if($iob eq "I" && $prev_cls ne $cls) {
	    die "IOB error: type change witout \"B\" ($prev_cls -> $cls)";
	}
	($prev_iob, $prev_cls) = ($iob, $cls);
    } # for
} # check_sequence
