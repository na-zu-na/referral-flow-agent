"""Offline PNG charts using Pillow; no provider, plotting service or network."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import OUT

NAVY="#17324D"
BLUE="#3274A1"
AMBER="#CB8735"
GREY="#667789"
WHITE="#FFFFFF"
W,H=1200,650
FONT=Path("C:/Windows/Fonts/arial.ttf")


def font(size, bold=False):
    path=Path("C:/Windows/Fonts/arialbd.ttf") if bold else FONT
    return ImageFont.truetype(str(path),size)


def canvas(title,subtitle):
    im=Image.new("RGB",(W,H),WHITE)
    d=ImageDraw.Draw(im)
    d.text((65,35),title,font=font(31,True),fill=NAVY)
    d.text((65,84),subtitle,font=font(19),fill=GREY)
    d.line((65,123,1140,123),fill="#DCE5EB",width=2)
    return im,d


def bar(name,title,subtitle,labels,series,unit,precision=2):
    im,d=canvas(title,subtitle)
    left,top,right,bottom=110,170,1120,525
    ymax=max(max(v) for _,v,_ in series)*1.18 if series else 1
    if ymax<=0: ymax=1
    for step in range(5):
        y=bottom-(bottom-top)*step/4
        d.line((left,y,right,y),fill="#E4EAF0",width=1)
        d.text((15,y-12),f"{ymax*step/4:,.{precision}f}",font=font(17),fill=GREY)
    n=len(labels); group=(right-left)/n
    bw=min(80,group/(len(series)+1))
    for i,label in enumerate(labels):
        center=left+group*(i+.5)
        for j,(sname,vals,color) in enumerate(series):
            x=center+(j-(len(series)-1)/2)*bw*1.2
            h=(bottom-top)*vals[i]/ymax
            d.rectangle((x-bw/2,bottom-h,x+bw/2,bottom),fill=color)
            d.text((x-bw/2,bottom-h-28),f"{vals[i]:,.{precision}f}",font=font(15),fill=NAVY)
        d.text((center-65,bottom+22),label,font=font(17),fill=NAVY)
    d.text((65,585),unit,font=font(16),fill=GREY)
    if len(series)>1:
        for j,(sname,_,color) in enumerate(series):
            x=700+j*210
            d.rectangle((x,580,x+18,598),fill=color)
            d.text((x+26,578),sname,font=font(16),fill=NAVY)
    im.save(OUT/"charts"/name)


def line(name,title,subtitle,labels,series,unit):
    im,d=canvas(title,subtitle)
    left,top,right,bottom=125,170,1080,515
    allvals=[v for _,vals,_ in series for v in vals]
    lo=min(allvals)*.9; hi=max(allvals)*1.05
    if hi==lo: hi=lo+1
    for step in range(5):
        y=bottom-(bottom-top)*step/4
        d.line((left,y,right,y),fill="#E4EAF0")
        d.text((18,y-10),f"{lo+(hi-lo)*step/4:,.0f}",font=font(17),fill=GREY)
    xs=[left+(right-left)*i/(len(labels)-1) for i in range(len(labels))]
    for x,label in zip(xs,labels):
        d.text((x-28,bottom+18),label,font=font(18),fill=NAVY)
    for idx,(sname,vals,color) in enumerate(series):
        pts=[(x,bottom-(v-lo)/(hi-lo)*(bottom-top)) for x,v in zip(xs,vals)]
        d.line(pts,fill=color,width=4)
        for x,y in pts: d.ellipse((x-6,y-6,x+6,y+6),fill=color)
        lx=115+(idx%2)*500; ly=575+(idx//2)*25
        d.rectangle((lx,ly,lx+18,ly+18),fill=color)
        d.text((lx+26,ly-3),sname,font=font(16),fill=NAVY)
    d.text((75,545),unit,font=font(16),fill=GREY)
    im.save(OUT/"charts"/name)


def make_charts(report: dict, sensitivity: list[dict], levers: list[dict], taxonomy: list[dict]) -> None:
    full=[s for s in report["model_summary"] if s["scope"]=="FULL_BATTERY" and s["prompt_version"]=="v2"]
    labels=["GPT","Qwen","Mistral","Gemini"]
    spend=report["evaluation_spend"]
    bar("evaluation_spend_reconciliation.png","Recorded selected-model evaluation charges",
        "Scored runs and extra provider-error attempt have different denominators",
        ["Scored 278","Extra error"],[("Recorded USD",[spend["selected_scored_run_spend"],
         spend["extra_charged_mistral_provider_error"]],BLUE)],"USD",precision=5)
    bar("ai_vs_fallback_cost.png","AI variable cost per referral",
        "Four full-battery V2 models; human fallback shown in separate monthly chart",
        labels,[("AI USD",[s["avg_provider_ai_cost_measured"] for s in full],BLUE)],"Provider-recorded USD / referral",precision=5)
    bar("monthly_cost_by_model.png","Evaluation-rate monthly scenarios",
        "4,000 referrals; fixed deployment cost USD 0 is an unmeasured baseline assumption",
        labels,[("Trial-weighted",[s["trial_weighted_monthly_cost"] for s in full],BLUE),
                ("Case-balanced",[s["case_balanced_monthly_cost"] for s in full],AMBER)],
        "Expected USD / 4,000 referrals")
    qtrial,qcase=report["qwen_prompt_ablation"]
    bar("qwen_v1_v2_cost_comparison.png","Qwen prompt control",
        "Matched 52-run keys; fallback translated from evaluation pass rates",
        ["Qwen V1","Qwen V2"],
        [("Trial-weighted",[qtrial["v1_monthly_scenario"],qtrial["v2_monthly_scenario"]],BLUE),
         ("Case-balanced",[qcase["v1_monthly_scenario"],qcase["v2_monthly_scenario"]],AMBER)],
        "Expected USD / 4,000 referrals")
    palette=[BLUE,AMBER,"#5B8D58","#7B6DAB"]
    line("sensitivity_monthly_cost.png","Success-rate sensitivity",
         "LOW / BASE / HIGH = measured pass rate ±10 percentage points, clamped",
         ["LOW","BASE","HIGH"],
         [(label,[next(z["monthly_variable_cost"] for z in sensitivity if z["experiment_id"]==s["experiment_id"] and z["scenario"]==scenario)
                  for scenario in ("LOW","BASE","HIGH")],palette[i])
          for i,(s,label) in enumerate(zip(full,labels))],
         "Expected USD / 4,000 referrals")
    bar("pass_rate_vs_cost_pareto.png","Full-battery evaluation pass rates",
        "Pareto cost/pass status is separate from price tier and safety",
        labels,[("Pass %",[s["trial_weighted_pass_rate"]*100 for s in full],BLUE)],
        "Passed / 52 (%)")
    bar("cost_lever_attribution.png","B / T / D / S evidence",
        "Bars indicate available observations, not additive dollar savings",
        ["B","T","D","S"],[("Evidence indicator",[1,1,1,1],BLUE)],
        "B/D not causally isolated; T from D2; S from Qwen control",precision=0)
    ids=[s["experiment_id"] for s in report["model_summary"]]
    short=["GPT","Qwen V2","Mistral","Gemini","Claude","Qwen V1"]
    invalid=[sum(r["experiment_id"]==bid and r["failure_category"]=="INVALID_MODEL_OUTPUT" for r in taxonomy) for bid in ids]
    bar("failure_taxonomy.png","Invalid model outputs",
        "All remain failures in the 278 selected scored runs",
        short,[("Invalid outputs",invalid,AMBER)],"Count",precision=0)
    neg=report["common_negative"]
    bar("common_negative_five_model.png","Five-model common negative subset",
        "18 matched case/trial keys per V2 model; not production prevalence",
        ["GPT","Qwen","Mistral","Gemini","Claude"],
        [("Pass %",[x["pass_rate"]*100 for x in neg],BLUE)],"Passed / 18 (%)")
