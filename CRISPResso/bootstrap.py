#!/usr/bin/env python 
'''
CRISPResso - Luca Pinello 2015
Software pipeline for the analysis of CRISPR-Cas9 genome editing outcomes from deep sequencing data
https://github.com/lucapinello/CRISPResso
'''
__version__ = "0.5.0"


import sys
import os
import subprocess as sb
import argparse
import logging
import re
import gzip
import cPickle as cp
from collections import defaultdict
import re

def main():
	print '  \n~~~CRISPResso~~~'
	print '-Analysis of CRISPR/CAS9 events from pair ended (PE) sequencing data-'
	print '''
			..
		  ..  ..
				..
				 ..
				..
			   ..
			 ..
	##       ..    ####
	##.............##  ##
	##.............##   ##
	##.............## ##
	##.............###
	 ##...........##
	  #############
	  #############
	#################'''
	print'\n[Luca Pinello 2015, send bugs, suggestions or *green coffee* to lucapinello AT gmail DOT com]\n\n',

	
	print 'Version %s\n' % __version__





	logging.basicConfig(level=logging.INFO,
						format='%(levelname)-5s @ %(asctime)s:\n\t %(message)s \n',
						datefmt='%a, %d %b %Y %H:%M:%S',
						stream=sys.stderr,
						filemode="w"
						)
	error   = logging.critical		
	warn    = logging.warning
	debug   = logging.debug
	info    = logging.info
	
	_ROOT = os.path.abspath(os.path.dirname(__file__))
	
	def get_data(path):
		return os.path.join(_ROOT, 'data', path)
	
	def check_library(library_name):
		try:
			return __import__(library_name)
		except:
			error('You need to install %s to use Crispresso!' % library_name)
			sys.exit(1)

	def which(program):
		import os
		def is_exe(fpath):
			return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

		fpath, fname = os.path.split(program)
		if fpath:
			if is_exe(program):
				return program
		else:
			for path in os.environ["PATH"].split(os.pathsep):
				path = path.strip('"')
				exe_file = os.path.join(path, program)
				if is_exe(exe_file):
					return exe_file

		return None

	def check_program(binary_name,download_url=None):
		if not which(binary_name):
			error('You need to install and have the command #####%s##### in your PATH variable to use Crispresso!\n Please read the documentation!' % binary_name)
			if download_url:
				error('You can download it from here:%s' % download_url)
			sys.exit(1)


	nt_complement=dict({'A':'T','C':'G','G':'C','T':'A','N':'N'})

	def reverse_complement(seq):
		return "".join([nt_complement[c] for c in seq.upper()[-1::-1]])


	def filter_fastq_by_qual(fastq_filename,min_bp_quality=10,output_filename=None):

		if fastq_filename.endswith('.gz'):
			fastq_handle=gzip.open(fastq_filename)
		else:
			fastq_handle=open(fastq_filename)

		if not output_filename:
			output_filename=fastq_filename.replace('.fastq','').replace('.gz','')+'_filtered.fastq.gz'

		with gzip.open(output_filename,'w+') as fastq_filtered_outfile:

			for record in SeqIO.parse(fastq_handle, "fastq"):
				if np.array(record.letter_annotations["phred_quality"]).mean()>=min_bp_quality:
				#if (sum(np.array((record.letter_annotations["phred_quality"]))<min_bp_quality)/float(len(record.letter_annotations["phred_quality"])))<1:
				#if min(record.letter_annotations["phred_quality"])>=min_bp_quality:
					fastq_filtered_outfile.write(record.format('fastq'))

		return output_filename

	trim_seq = lambda x: x[args.exclude_bp_from_sides:len(x)-args.exclude_bp_from_sides]


	plt=check_library('pylab')
	from matplotlib import font_manager as fm

	pd=check_library('pandas')
	np=check_library('numpy')
	Bio=check_library('Bio')

	check_program('java')
	check_program('flash')
	check_program('needle')

	from Bio import SeqIO

	parser = argparse.ArgumentParser(description='CRISPResso Parameters')
	parser.add_argument('-r1','--fastq_r1', type=str,  help='First fastq file', required=True )
	parser.add_argument('-r2','--fastq_r2', type=str,  help='Second fastq file for paired end reads',default='')
	parser.add_argument('-a','--amplicon_seq', type=str,  help='Amplicon Sequence', required=True)

	#optional
	parser.add_argument('-g','--guide_seq',  help='sgRNA sequence', default='')
	parser.add_argument('-d','--donor_seq',  help='Amplicon sequence expected after an HDR', default='')
	parser.add_argument('--min_bp_quality', type=int, help='Minimum average quality score (phred33) to keep a read', default=0)
	parser.add_argument('--min_identity_score', type=float, help='Min identity score for the alignment', default=50.0)
	parser.add_argument('-n','--name',  help='Output name', default='')
	parser.add_argument('--max_insertion_size',  type=int, help='Max insertion size tolerated for merging paired end reads', default=60)
	parser.add_argument('--HDR_perfect_alignment_threshold',  type=float, help='Sequence homology %% for an HDR occurence', default=98.0)
	parser.add_argument('--trim_sequences',help='Trim Illumina Adapters with Trimmomatic',action='store_true')
	parser.add_argument('--trimmomatic_options_string', type=str, help='Override options for Trimmomatic',default=' ILLUMINACLIP:%s:0:90:10:0:true MINLEN:40' % get_data('NexteraPE-PE.fa'))
	parser.add_argument('--needle_options_string',type=str,help='Override options for Needle aligner',default='-gapopen=10 -gapextend=0.5  -awidth3=5000')
	parser.add_argument('--keep_intermediate',help='Keep all the  intermediate files',action='store_true')
	parser.add_argument('-o','--output_folder',  help='', default='')
	parser.add_argument('--dump',help='Dump numpy arrays to file for the quantifications of indels',action='store_true')
	parser.add_argument('--exclude_bp_from_sides', type=int, help='Exclude bp from each side for the quantificaton of the indels', default=0)
	parser.add_argument('--save_also_png',help='Save also .png images additionaly to .pdf files',action='store_true')

	args = parser.parse_args()
	
	#make evetything uppercase!
	if args.amplicon_seq:
		args.amplicon_seq=args.amplicon_seq.upper()
	
	if args.donor_seq:
		args.donor_seq=args.donor_seq.upper()

	if args.guide_seq:
		args.guide_seq=args.guide_seq.upper()
		cut_points=[m.start() +len(args.guide_seq)-3 for m in re.finditer(args.guide_seq, args.amplicon_seq)]+[m.start() +2 for m in re.finditer(reverse_complement(args.guide_seq), args.amplicon_seq)]

		if not cut_points:
			error('The guide sequences provided is not present in the amplicon sequence! \n\nPlease check your input!')
			sys.exit(1)
		info('Cut Points from guide seq:%s' % cut_points)
	else:
		cut_points=[]


	get_name_from_fasta=lambda  x: os.path.basename(x).replace('.fastq','').replace('.gz','')

	if not args.name:
		database_id='%s_%s' % (get_name_from_fasta(args.fastq_r1),get_name_from_fasta(args.fastq_r2))
	else:
		database_id=args.name

	OUTPUT_DIRECTORY='CRISPResso_on_%s' % database_id

	if args.output_folder:
		OUTPUT_DIRECTORY=os.path.join(os.path.abspath(args.output_folder),OUTPUT_DIRECTORY)
	
	_jp=lambda filename: os.path.join(OUTPUT_DIRECTORY,filename) #handy function to put a file in the output directory

	try:
		info('Creating Folder %s' % OUTPUT_DIRECTORY)
		os.makedirs(OUTPUT_DIRECTORY)
		info('Done!')
	except:
		warn('Folder %s already exists.' % OUTPUT_DIRECTORY)

	log_filename=_jp('CRISPResso_RUNNING_LOG.txt')

	with open(log_filename,'w+') as outfile:
		outfile.write('[Command used]:\nCRISPResso %s\n\n\n[Other tools log]:\n' % ' '.join(sys.argv))

	if args.min_bp_quality>0:
		info('Filtering reads with bp quality < %d ...' % args.min_bp_quality)
		args.fastq_r1=filter_fastq_by_qual(args.fastq_r1,min_bp_quality=args.min_bp_quality,output_filename=_jp(os.path.basename(args.fastq_r1).replace('.fastq','').replace('.gz','')+'_filtered.fastq.gz'))
		if args.fastq_r2!='':
			args.fastq_r2=filter_fastq_by_qual(args.fastq_r2,min_bp_quality=args.min_bp_quality,output_filename=_jp(os.path.basename(args.fastq_r2.replace('.fastq','')).replace('.gz','')+'_filtered.fastq.gz'))


	processed_output_filename=_jp('out.extendedFrags.fastq')
	
	
	if args.fastq_r2=='': #single end reads
	    
	    #check if we need to trim
	    if not args.trim_sequences:
	        output_forward_filename=args.fastq_r1
	    else:
	        output_forward_filename=_jp('reads.trimmed.fq')
	        #Trimming with trimmomatic
	        cmd='java -jar %s SE -phred33 %s  %s %s >>%s 2>&1'\
	        % (get_data('trimmomatic-0.33.jar'),args.fastq_r1,
	           output_forward_filename,
	           args.trimmomatic_options_string.replace('NexteraPE-PE.fa','TruSeq3-SE.fa'),
	           log_filename)
	        #print cmd
	        sb.call(cmd,shell=True)
	        info('Done!')
	
	    #write a dict of lenghts like the flash tools    
	    dict_lengths=defaultdict(lambda:0)
	    if args.fastq_r2.endswith('.gz'):
	        fastq_handle=gzip.open(output_forward_filename)
	    else:
	        fastq_handle=open(output_forward_filename)
	
	    with open(_jp('out.extendedFrags.fastq'),'w+') as outfile:
	        line=fastq_handle.readline()
	        outfile.write(line)
	        for idx,line in enumerate(fastq_handle):
	            outfile.write(line)
	else:#paired end reads case
	
	    if not args.trim_sequences:
	        output_forward_paired_filename=args.fastq_r1
	        output_reverse_paired_filename=args.fastq_r2
	    else:
	        info('Trimming sequences with Trimmomatic...')
	        output_forward_paired_filename=_jp('output_forward_paired.fq')
	        output_forward_unpaired_filename=_jp('output_forward_unpaired.fq') 
	        output_reverse_paired_filename=_jp('output_reverse_paired.fq') 
	        output_reverse_unpaired_filename=_jp('output_reverse_unpaired.fq')
	
	        #Trimming with trimmomatic
	        cmd='java -jar %s PE -phred33 %s  %s %s  %s  %s  %s %s >>%s 2>&1'\
	        % (get_data('trimmomatic-0.33.jar'),
			args.fastq_r1,args.fastq_r2,output_forward_paired_filename,
			output_forward_unpaired_filename,output_reverse_paired_filename,
			output_reverse_unpaired_filename,args.trimmomatic_options_string,log_filename)
	        #print cmd
	        sb.call(cmd,shell=True)
	        info('Done!')
	
	    #Merging with Flash
	    info('Merging paired sequences with Flash...')
	    if args.donor_seq:
	        len_amplicon=len(args.donor_seq)+args.max_insertion_size #considering some tolerance for new insertion
	    else:
	        len_amplicon=len(args.amplicon_seq)+args.max_insertion_size #considering some tolerance for new insertion
	
	
	    cmd='flash %s %s --min-overlap=1 --max-overlap=%s -d %s >>%s 2>&1' %\
	         (output_forward_paired_filename,output_reverse_paired_filename,len_amplicon,OUTPUT_DIRECTORY,log_filename)
	    sb.call(cmd,shell=True)
	    info('Done!')
	
	    flash_hist_filename=_jp('out.hist')
	    flash_histogram_filename=_jp('out.histogram')
	    flash_not_combined_1_filename=_jp('out.notCombined_1.fastq')
	    flash_not_combined_2_filename=_jp('out.notCombined_2.fastq')
	

	len_amplicon=len(args.amplicon_seq)


	info('Preparing files for the alignment...')
	#parsing flash output and prepare the files for alignment
	data_to_parse=[]
	with open(processed_output_filename) as r1_file:
		for idx,line in enumerate(r1_file):
			if (idx % 4) ==0:
				seq_id=line.split()[0]
			if (idx % 4) ==1:
				seq=line.strip()
			if (idx %4) == 3:
				qual=line.strip()
				data_to_parse.append((seq_id,seq,qual))
	df_R1R2=pd.DataFrame(data_to_parse,columns=['ID','SEQ_R1R2','QUAL_R1R2']).set_index('ID')


	database_fasta_filename=_jp('%s_database.fa' % database_id)
	query_fasta_filename=_jp('%s_query.fa' % database_id)
	needle_output_filename=_jp('needle_output_%s.txt' % database_id)
	crispresso_output_filename=_jp('CRISPRresso_aligned_%s.txt' % database_id)

	#write .fa files
	with open(database_fasta_filename,'w+') as outfile:
		outfile.write('>%s\n%s\n' % (database_id,args.amplicon_seq))

	with open(query_fasta_filename,'w+') as outfile:
		for seq_id,row in df_R1R2.iterrows():
			outfile.write('>%s\n%s\n' % (seq_id.replace(':','_')+'_R1R2',row['SEQ_R1R2']))

	if args.donor_seq:
		database_repair_fasta_filename=_jp('%s_database_repair.fa' % database_id)
		needle_output_repair_filename=_jp('needle_output_repair_%s.txt' % database_id)
	
		with open(database_repair_fasta_filename,'w+') as outfile:
			outfile.write('>%s\n%s\n' % (database_id,args.donor_seq))
	info('Done!')

	def parse_needle_output(needle_filename,name='seq',just_score=False):
		needle_data=[]

		with open(needle_filename) as needle_infile:

			line=needle_infile.readline()
			while line:

				while line and ('# Aligned_sequences' not  in line):
					line=needle_infile.readline()

				if line:
					#print line
					needle_infile.readline() #skip another line

					line=needle_infile.readline()
					id_seq=line.split()[-1].replace('_',':')

					for _ in range(5):
						needle_infile.readline()

					line=needle_infile.readline()
				
					identity_seq=eval(line.strip().split(' ')[-1].replace('%','').replace(')','').replace('(',''))
					
					if just_score:
						needle_data.append([id_seq,identity_seq])
					else:
						for _ in range(7):
							needle_infile.readline()

						line=needle_infile.readline()
						aln_ref_seq=line.split()[2]


						aln_str=needle_infile.readline()[21:].rstrip()
						line=needle_infile.readline()
						aln_query_seq=line.split()[2]
						aln_query_len=line.split()[3]
						needle_data.append([id_seq,identity_seq,aln_query_len,aln_ref_seq,aln_str,aln_query_seq])

			if just_score:
				return pd.DataFrame(needle_data,columns=['ID','score_'+name]).set_index('ID')
			else:
				return pd.DataFrame(needle_data,columns=['ID','score_'+name,'length','ref_seq','align_str','align_seq']).set_index('ID')


	info('Aligning sequences...')
	#Alignment here
	cmd='needle -asequence=%s -bsequence=%s -outfile=%s %s >>%s 2>&1' \
		 %(database_fasta_filename,query_fasta_filename,needle_output_filename,args.needle_options_string,log_filename)
	sb.call(cmd,shell=True)

	#If we have a donor sequence we just compare the fq in the two cases and exit
	N_REPAIRED=0
	if args.donor_seq:

		cmd='needle -asequence=%s -bsequence=%s -outfile=%s %s >>%s 2>&1'\
			 %(database_repair_fasta_filename,query_fasta_filename,needle_output_repair_filename,args.needle_options_string,log_filename)
		sb.call(cmd,shell=True)
		info('Done!')

		info('Parsing aligned files and making plots...')
		df_database=parse_needle_output(needle_output_filename,'ref')
		df_database_repair=parse_needle_output(needle_output_repair_filename,'repaired',just_score=True)
		df_database_and_repair=df_database.join(df_database_repair) 

		#filter bad alignments
		df_database_and_repair=df_database_and_repair.ix[(df_database_and_repair.score_ref>args.min_identity_score)|(df_database_and_repair.score_repaired>args.min_identity_score)]

		df_database_and_repair['score_diff']=df_database_and_repair.score_ref-df_database_and_repair.score_repaired

		N_REPAIRED=sum((df_database_and_repair.score_diff<0) & (df_database_and_repair.score_repaired>=args.HDR_perfect_alignment_threshold))

		#df_database_and_repair.ix[:,['score_ref','score_repaired','score_diff']].to_csv(_jp('CRISPResso_SUMMARY_ALIGNMENT_IDENTITY_SCORE.txt'),header=['Identity_amplicon', 'Indentity_repaired_amplicon','Difference'],sep='\t')
		df_repaired=df_database_and_repair.ix[(df_database_and_repair.score_diff<0) & (df_database_and_repair.score_repaired>=args.HDR_perfect_alignment_threshold)].sort('score_repaired',ascending=False)
		df_repaired.ix[:,['score_ref','score_repaired','score_diff']].to_csv(_jp('CRISPResso_REPAIRED_ONLY_IDENTITY_SCORE.txt'),header=['Identity_amplicon', 'Indentity_repaired_amplicon','Difference'],sep='\t')

	#info('Parsing aligned files and making plots...')
	#here we cover the case of the mutations plot instead..

	#remove the HR events
	if args.donor_seq:
		df_needle_alignment=df_database_and_repair.ix[df_database_and_repair.index.difference(df_repaired.index)]
		N_TOTAL=df_database_and_repair.shape[0]*1.0

	else:
		df_needle_alignment=parse_needle_output(needle_output_filename,'ref')
		#filter out not aligned reads
		df_needle_alignment=df_needle_alignment.ix[df_needle_alignment.score_ref>args.min_identity_score]
		N_TOTAL=df_needle_alignment.shape[0]*1.0 #THIS SHOULD BE FIXED


	if N_TOTAL==0:
		error('Zero sequences aligned')
		info('All Done!')
		print'''     
				 )             
				(              
			   __)__           
			C\|     \          
			  \     /          
			   \___/
		'''
		sys.exit(1)
	

	check_seq_modified=lambda aln_str: 0 if (len(set(trim_seq(aln_str)))==1) else 1
	
	df_needle_alignment['n_inserted']=df_needle_alignment['ref_seq'].apply(lambda x: trim_seq(x).count('-'))
	df_needle_alignment['n_deleted']=df_needle_alignment['align_seq'].apply(lambda x: trim_seq(x).count('-'))
	df_needle_alignment['n_mutated']=df_needle_alignment['align_str'].apply(lambda x: trim_seq(x).count('.'))
	df_needle_alignment['effective_len']=df_needle_alignment['align_seq'].apply(lambda x: len(x.replace('-','')))
	df_needle_alignment['NHEJ']=df_needle_alignment.ix[:,['n_inserted','n_deleted','n_mutated']].sum(1)>0

	N_MODIFIED=df_needle_alignment['NHEJ'].sum()
	N_UNMODIFIED=N_TOTAL-N_MODIFIED    

	info('Calculating indel distribution based on the length of the reads...')
	
	if args.guide_seq:
	    min_cut=min(cut_points)
	    max_cut=max(cut_points)
	    xmin,xmax=-min_cut,len_amplicon-max_cut
	else:
	    min_cut=len_amplicon/2
	    max_cut=len_amplicon/2
	    xmin,xmax=-min_cut,+max_cut
	
	
	hdensity,hlengths=np.histogram(df_needle_alignment.effective_len-len_amplicon,np.arange(xmin,xmax))
	hlengths=hlengths[:-1]
	center_index=np.nonzero(hlengths==0)[0][0]
	
	plt.figure()
	plt.bar(0,hdensity[center_index],color='red',linewidth=0)
	plt.hold(True)
	barlist=plt.bar(hlengths,hdensity,align='center',linewidth=0)
	barlist[center_index].set_color('r')
	plt.xlim([xmin,xmax])
	plt.ylabel('Sequences (no.)')
	plt.xlabel('Indel size (bp)')
	plt.ylim([0,hdensity.max()*1.2])
	plt.title('Indel size distribution')
	plt.legend(['Unmodified','Modified'])
	plt.savefig(_jp('1a.Indel_size_distribution_n_sequences.pdf'))
	if args.save_also_png:
		plt.savefig(_jp('1a.Indel_size_distribution_n_sequences.png'))
	
	
	plt.figure()
	plt.bar(0,hdensity[center_index]/(float(hdensity.sum()))*100.0,color='red',linewidth=0)
	plt.hold(True)
	barlist=plt.bar(hlengths,hdensity/(float(hdensity.sum()))*100.0,align='center',linewidth=0)
	barlist[center_index].set_color('r')
	plt.xlim([xmin,xmax])
	plt.ylabel('Sequences (%)')
	plt.xlabel('Indel size (bp)')
	plt.title('Indel size distribution')
	plt.legend(['Unmodified','Modified'])
	plt.savefig(_jp('1b.Indel_size_distribution_percentage.pdf'))
	if args.save_also_png:
		plt.savefig(_jp('1b.Indel_size_distribution_percentage.png'))
	info('Done!')
	
	info('Quantifying indels...')

	if args.donor_seq:
		fig=plt.figure(figsize=(12,12))
		ax=fig.add_subplot(1,1,1)
		patches, texts, autotexts =ax.pie([N_UNMODIFIED,N_MODIFIED,N_REPAIRED],labels=['Unmodified\n(%d reads)' %N_UNMODIFIED,'NHEJ\n(%d reads)' % N_MODIFIED, 'HDR\n(%d reads)' %N_REPAIRED],explode=(0,0.05,0.1),colors=[(1,0,0,0.2),(0,0,1,0.2),(0,1,0,0.2)],autopct='%1.1f%%')
		proptease = fm.FontProperties()
		proptease.set_size('xx-large')
		plt.setp(autotexts, fontproperties=proptease)
		plt.setp(texts, fontproperties=proptease)
		plt.savefig(_jp('2.Unmodified_NHEJ_HR_pie_chart.pdf'))
		if args.save_also_png:
			plt.savefig(_jp('2.Unmodified_NHEJ_HR_pie_chart.png'))

	else:
		fig=plt.figure(figsize=(12,12))
		ax=fig.add_subplot(1,1,1)
		patches, texts, autotexts =ax.pie([N_UNMODIFIED/N_TOTAL*100,N_MODIFIED/N_TOTAL*100],labels=['Unmodified\n(%d reads)' %N_UNMODIFIED,'NHEJ\n(%d reads)' % N_MODIFIED],explode=(0,0.05),colors=[(1,0,0,0.2),(0,0,1,0.2)],autopct='%1.1f%%')
		proptease = fm.FontProperties()
		proptease.set_size('xx-large')
		plt.setp(autotexts, fontproperties=proptease)
		plt.setp(texts, fontproperties=proptease)
		plt.savefig(_jp('2.Unmodified_NHEJ_pie_chart.pdf'))
		if args.save_also_png:
			plt.savefig(_jp('2.Unmodified_NHEJ_pie_chart.png'))


	#(1) a graph of frequency of deletions and insertions of various sizes (deletions could be consider as negative numbers and insertions as positive);
	y_values_mut,x_bins=plt.histogram(df_needle_alignment['n_mutated'],bins=range(0,60))
	y_values_ins,x_bins=plt.histogram(df_needle_alignment['n_inserted'],bins=range(0,60))
	y_values_del,x_bins=plt.histogram(df_needle_alignment['n_deleted'],bins=range(0,60))

	fig=plt.figure(figsize=(20,10))

	ax=fig.add_subplot(2,3,1)
	ax.bar(x_bins[:-1],y_values_ins,align='center',linewidth=0)
	barlist=ax.bar(x_bins[:-1],y_values_ins,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.title('Insertions')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (no.)')
	plt.legend(['Non-insertion','Insertion'][::-1])

	ax=fig.add_subplot(2,3,2)
	ax.bar(-x_bins[:-1],y_values_del,align='center',linewidth=0)
	barlist=ax.bar(-x_bins[:-1],y_values_del,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.title('Deletions')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (no.)')
	plt.legend(['Non-deletion','Deletion'][::-1],loc=2)


	ax=fig.add_subplot(2,3,3)
	ax.bar(x_bins[:-1],y_values_mut,align='center',linewidth=0)
	barlist=ax.bar(x_bins[:-1],y_values_mut,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.title('Substitutions')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (no.)')
	plt.legend(['Non-substitution','Substitution'][::-1])

	ax=fig.add_subplot(2,3,4)
	ax.bar(x_bins[:-1],y_values_ins/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist=ax.bar(x_bins[:-1],y_values_ins/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (%)')
	plt.legend(['Non-insertion','Insertion'][::-1])

	ax=fig.add_subplot(2,3,5)
	ax.bar(-x_bins[:-1],y_values_del/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist=ax.bar(-x_bins[:-1],y_values_del/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (%)')
	plt.legend(['Non-deletion','Deletion'][::-1],loc=2)

	ax=fig.add_subplot(2,3,6)
	ax.bar(x_bins[:-1],y_values_mut/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist=ax.bar(x_bins[:-1],y_values_mut/float(df_needle_alignment.shape[0])*100.0,align='center',linewidth=0)
	barlist[0].set_color('r')
	plt.xlabel('Size (bp)')
	plt.ylabel('Sequences (%)')
	plt.legend(['Non-substitution','Substitution'][::-1])


	plt.savefig(_jp('3.Insertion_Deletion_Substitutions_size_hist.pdf'))
	if args.save_also_png:
		plt.savefig(_jp('3.Insertion_Deletion_Substitutions_size_hist.png'))


	#(2) another graph with the frequency that each nucleotide within the amplicon was modified in any way (perhaps would consider insertion as modification of the flanking nucleotides);
	def compute_ref_positions(ref_seq):
		pos_idxs=[]
		idx=0
		for c in ref_seq:
			if c in set(['A','T','C','G']):
				pos_idxs.append(idx)
				idx+=1
			else:
				if idx==0:
					pos_idxs.append(-1)
				else:   
					pos_idxs.append(-idx)
		return np.array(pos_idxs)

	#compute positions relative to alignmnet
	df_needle_alignment['ref_positions']=df_needle_alignment['ref_seq'].apply(compute_ref_positions)

	
	#now check the location of the mutations
	
	re_find_indels=re.compile("(-*-)")
	re_find_substitutions=re.compile("(\.*\.)")
	flatten_positions=lambda x:np.ndarray.flatten(np.array([x for x in x]))
	
	effect_vector_insertion=np.zeros(len_amplicon)
	effect_vector_deletion=np.zeros(len_amplicon)
	effect_vector_mutation=np.zeros(len_amplicon)
	effect_vector_any=np.zeros(len_amplicon)
	
	exclude_idxs=range(args.exclude_bp_from_sides)+range(len(args.amplicon_seq)-args.exclude_bp_from_sides,len(args.amplicon_seq))

	for idx_row,row in df_needle_alignment.iterrows():
	
	    #quantify substitution
	    substitution_positions=[]
	    for p in re_find_substitutions.finditer(row.align_str):
	        #print p.span()
	        st,en=p.span()
	        substitution_positions.append(row.ref_positions[st:en])
	    
	    if substitution_positions:
	        substitution_positions=np.hstack(substitution_positions)
	        substitution_positions=np.setdiff1d(substitution_positions,exclude_idxs)
	        effect_vector_mutation[substitution_positions]+=1
	
	    #quantify deletion
	    deletion_positions=[]
	    for p in re_find_indels.finditer(row.align_seq):
	        #print p.span()
	        st,en=p.span()
	        deletion_positions.append(row.ref_positions[st:en])
	    
	    if deletion_positions:
	        deletion_positions=np.hstack(deletion_positions)
	        deletion_positions=np.setdiff1d(deletion_positions,exclude_idxs)
	        effect_vector_deletion[deletion_positions]+=1
	
	    #quantify insertion
	    insertion_positions=[]
	    for p in re_find_indels.finditer(row.ref_seq):
	        #print p.span()
	        st,en=p.span()
	        ref_st=row.ref_positions[st-1]
	        try:
	            ref_en=row.ref_positions[en]
	        except:
	            ref_en=len_amplicon-1
	
	        insertion_positions+=[ref_st,ref_en]
	    
	    if insertion_positions:
	        insertion_positions=np.hstack(insertion_positions)
	        insertion_positions=np.setdiff1d(insertion_positions,exclude_idxs)
	        effect_vector_insertion[insertion_positions]+=1
	    
	    any_positions=np.unique(np.hstack([deletion_positions,insertion_positions,substitution_positions])).astype(int)
	    effect_vector_any[any_positions]+=1
	
	#make plots
	plt.figure()
	plt.plot(effect_vector_insertion,'r',lw=2)
	plt.hold(True)
	plt.plot(effect_vector_deletion,'m',lw=2)
	plt.plot(effect_vector_mutation,'g',lw=2)
	labels_plot=['Insertions','Deletions','Substitutions']
	
	y_max=max(max(effect_vector_insertion),max(effect_vector_deletion),max(effect_vector_mutation))*1.2
	
	
	if cut_points:
	    for cut_point in cut_points:
	        plt.plot([cut_point,cut_point],[0,y_max],'--k',lw=2)
	    lgd=plt.legend(labels_plot+['Predicted cleavage position'],loc='center', bbox_to_anchor=(0.5, -0.28),ncol=1, fancybox=True, shadow=True)
	
	else:
	    lgd=plt.legend(labels_plot)
	
	
	plt.xlabel('Amplicon position bp)')
	plt.ylabel('Sequences (no.)')
	plt.ylim(ymax=y_max)
	plt.xlim(xmax=len(args.amplicon_seq))
	plt.title('Indel position distribution')
	plt.savefig(_jp('4.Insertion_Deletion_Substitution_Locations.pdf'),bbox_extra_artists=(lgd,), bbox_inches='tight')
	if args.save_also_png:
		plt.savefig(_jp('4.Insertion_Deletion_Substitution_Locations.png'),bbox_extra_artists=(lgd,), bbox_inches='tight')
	
	plt.figure()
	
	effect_vector_combined=100*effect_vector_any/float(N_TOTAL)
	#effect_vector_combined=100*effect_vector_any/float((df_needle_alignment.shape[0]-len(problematic_seq)))
	
	y_max=max(effect_vector_combined)*1.2
	
	plt.plot(effect_vector_combined,'r',lw=2)
	plt.hold(True)  
	
	if cut_points:
	    for cut_point in cut_points:
	        plt.plot([cut_point,cut_point],[0,y_max],'--k',lw=2)
	    lgd=plt.legend(['Predicted cleavage position'],loc='center', bbox_to_anchor=(0.5, -0.18),ncol=1, fancybox=True, shadow=True)
	
	plt.title('Indel position distribution')
	plt.xlabel('Amplicon position (bp)')
	plt.ylabel('Sequences (%)')
	plt.ylim(ymax=y_max)
	plt.xlim(xmax=len(args.amplicon_seq))
	plt.savefig(_jp('5.Combined_Insertion_Deletion_Substitution_Locations.pdf'),bbox_extra_artists=(lgd,), bbox_inches='tight')
	if args.save_also_png:
		plt.savefig(_jp('5.Combined_Insertion_Deletion_Substitution_Locations.png'),bbox_extra_artists=(lgd,), bbox_inches='tight')
	
	info('Done!')

	if not args.keep_intermediate:
	    info('Removing Intermediate files...')
	    
	    if args.fastq_r2!='':
	    	files_to_remove=[output_forward_paired_filename,output_reverse_paired_filename,\
	                     processed_output_filename,flash_hist_filename,flash_histogram_filename,\
	                     flash_not_combined_1_filename,flash_not_combined_2_filename,\
	                     database_fasta_filename,query_fasta_filename] 
	    else:
	    	files_to_remove=[processed_output_filename,database_fasta_filename,query_fasta_filename] 
	
	    if args.trim_sequences and args.fastq_r2!='':
	        files_to_remove+=[output_forward_unpaired_filename,output_reverse_unpaired_filename]
	
	    if not args.dump:
	        files_to_remove+=[needle_output_filename]
	        if args.donor_seq:
	            files_to_remove+=[needle_output_repair_filename]
	
	    if args.donor_seq:
	        files_to_remove+=[database_repair_fasta_filename,]
	
	    if args.min_bp_quality>0:
	    	if args.fastq_r2!='':
	        	files_to_remove+=[args.fastq_r1,args.fastq_r2]
	        else:
		        files_to_remove+=[args.fastq_r1]
	
	    for file_to_remove in files_to_remove:
	        os.remove(file_to_remove)
	
	#wrte effect vectors as plain text files
	def save_vector_to_file(vector,name):
		np.savetxt(_jp('%s.txt' %name), np.vstack([(np.arange(len(vector))+1),effect_vector_any]).T, fmt=['%d','%.18e'],delimiter='\t', newline='\n', header='amplicon position\teffect',footer='', comments='# ')


	with open(_jp('Quantification_of_editing_frequency.txt'),'w+') as outfile:
		outfile.write('Quantification of editing frequency:\n\tUnmodified:%d reads\n\tNHEJ:%d reads\n\tHDR:%d reads\n\tTOTAL:%d reads' %(N_UNMODIFIED, N_MODIFIED ,N_REPAIRED ,N_TOTAL))
	
	
	save_vector_to_file(effect_vector_insertion,'effect_vector_insertion')	
	save_vector_to_file(effect_vector_deletion,'effect_vector_deletion')	
	save_vector_to_file(effect_vector_mutation,'effect_vector_substitution')	
	save_vector_to_file(effect_vector_combined,'effect_vector_combined')	
	
		
	if args.dump:
	    info('Dumping all the processed data...')
	    np.savez(_jp('effect_vector_insertion'),effect_vector_insertion)
	    np.savez(_jp('effect_vector_deletion'),effect_vector_deletion)
	    np.savez(_jp('effect_vector_substitution'),effect_vector_mutation)
	    np.savez(_jp('effect_vector_combined'),effect_vector_combined)
	    cp.dump({'N_UNMODIFIED':N_UNMODIFIED,'N_MODIFIED':N_MODIFIED,'N_REPAIRED':N_REPAIRED,'N_TOTAL':N_TOTAL},open(_jp('COUNTS.cpickle'),'w+'))
	    df_needle_alignment.to_pickle(_jp('df_needle_alignment'))        
	
	info('All Done!')
	print'''     
	         )             
	        (              
	       __)__           
	    C\|     \          
	      \     /          
	       \___/
	'''
	sys.exit(0)