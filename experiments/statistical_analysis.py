"""Paired statistical comparisons for synthetic simulation outcomes."""
from __future__ import annotations
import math

def _ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i]);ranks=[0.0]*len(values);i=0
    while i<len(order):
        j=i
        while j+1<len(order) and values[order[j+1]]==values[order[i]]:j+=1
        rank=(i+j+2)/2
        for k in range(i,j+1):ranks[order[k]]=rank
        i=j+1
    return ranks

def _normal_p(z):return math.erfc(abs(z)/math.sqrt(2))

def _beta_fraction(a,b,x):
    qab=a+b;qap=a+1;qam=a-1;c=1.0;d=1-qab*x/qap
    d=1e-300 if abs(d)<1e-300 else d;d=1/d;h=d
    for m in range(1,201):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2));d=1+aa*d;d=1e-300 if abs(d)<1e-300 else d;d=1/d
        c=1+aa/c;c=1e-300 if abs(c)<1e-300 else c;h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2));d=1+aa*d;d=1e-300 if abs(d)<1e-300 else d;d=1/d
        c=1+aa/c;c=1e-300 if abs(c)<1e-300 else c;delta=d*c;h*=delta
        if abs(delta-1)<3e-14:break
    return h

def _regularized_beta(x,a,b):
    if x<=0:return 0.0
    if x>=1:return 1.0
    front=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x))
    if x<(a+1)/(a+b+2):return front*_beta_fraction(a,b,x)/a
    return 1-front*_beta_fraction(b,a,1-x)/b

def _student_t_p(t,degrees_freedom):
    if degrees_freedom<=0:return 1.0
    x=degrees_freedom/(degrees_freedom+t*t)
    return _regularized_beta(x,degrees_freedom/2,.5)

def paired_comparison(left,right):
    if len(left)!=len(right) or not left:raise ValueError("paired samples must be non-empty and aligned")
    differences=[float(a)-float(b) for a,b in zip(left,right)];n=len(differences)
    mean=sum(differences)/n
    variance=sum((x-mean)**2 for x in differences)/(n-1) if n>1 else 0
    sd=math.sqrt(variance);dz=mean/sd if sd else (0.0 if mean==0 else math.copysign(float("inf"),mean))
    centered=[x-mean for x in differences];third=sum(x**3 for x in centered)/n
    skew=third/(sd**3) if sd else 0
    if n>=3 and abs(skew)<1:
        statistic=mean/(sd/math.sqrt(n)) if sd else 0.0
        p=_student_t_p(statistic,n-1) if sd else (1.0 if mean==0 else 0.0);test="paired_t"
        rank_effect=None
    else:
        nonzero=[x for x in differences if x];ranks=_ranks([abs(x) for x in nonzero])
        positive=sum(rank for rank,value in zip(ranks,nonzero) if value>0);negative=sum(rank for rank,value in zip(ranks,nonzero) if value<0)
        statistic=min(positive,negative);den=len(nonzero)*(len(nonzero)+1)/2
        rank_effect=(positive-negative)/den if den else 0.0
        variance_w=len(nonzero)*(len(nonzero)+1)*(2*len(nonzero)+1)/24
        p=_normal_p((positive-den/2)/math.sqrt(variance_w)) if variance_w else 1.0;test="wilcoxon"
    return {"test":test,"n":n,"statistic":round(statistic,6),"p_value":round(min(1,p),6),
      "mean_difference":round(mean,6),"cohens_dz":dz,"rank_effect_size":rank_effect,
      "synthetic_outcomes":True}

def holm_correction(results,alpha=.05):
    ordered=sorted(enumerate(results),key=lambda item:item[1]["p_value"]);adjusted=[0.0]*len(results);running=0
    for rank,(index,row) in enumerate(ordered):
        value=min(1.0,(len(results)-rank)*row["p_value"]);running=max(running,value);adjusted[index]=running
    return [{**row,"holm_adjusted_p":round(adjusted[index],6),"reject_holm":adjusted[index]<alpha}
      for index,row in enumerate(results)]

def compare_paired_rows(rows,group_field,reference,comparators,metric,pair_fields=("profile","repetition")):
    lookup={(row[group_field],)+tuple(row[field] for field in pair_fields):row for row in rows};results=[]
    for comparator in comparators:
        keys=sorted(key[1:] for key in lookup if key[0]==reference and (comparator,)+key[1:] in lookup)
        left=[lookup[(reference,)+key][metric] for key in keys];right=[lookup[(comparator,)+key][metric] for key in keys]
        results.append({"reference":reference,"comparator":comparator,"metric":metric,**paired_comparison(left,right)})
    return holm_correction(results)
