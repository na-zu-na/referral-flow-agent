import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root=path.dirname(fileURLToPath(import.meta.url));
const report=JSON.parse(await fs.readFile(path.join(root,"outputs/cost_report.json"),"utf8"));
const wb=Workbook.create();
const names=["Executive_Summary","Model_Cost","Prompt_Impact","Evaluation_Spend","Sensitivity",
             "Break_Even","Uncertainty","Cost_Levers","Safety_Reliability","Cost_Guardrails","Methodology_Limits"];
const sheets=Object.fromEntries(names.map(name=>[name,wb.worksheets.add(name)]));
const navy="#17324D", blue="#3274A1", light="#EAF1F6", ink="#243746", amber="#FFF2D9";
const money='"USD "0.00000000', money6='"USD "0.000000', monthly='"USD "#,##0.00';
const full=report.model_summary.filter(x=>x.scope==="FULL_BATTERY"&&x.prompt_version==="v2");
const claude=report.model_summary.find(x=>x.scope==="FRONTIER_NEGATIVE_ONLY");
const labels=["GPT-4o-mini","Qwen 3 30B","Mistral Small 3.2","Gemini 2.5 Flash"];

function cell(sh,address,value){sh.getRange(address).values=[[value]]}
function formula(sh,address,value){sh.getRange(address).formulas=[[value]]}
function rows(sh,row,headers,data){
  const n=headers.length;
  sh.getRangeByIndexes(row-1,0,1,n).values=[headers];
  if(data.length) sh.getRangeByIndexes(row,0,data.length,n).values=data;
  const header=sh.getRangeByIndexes(row-1,0,1,n);
  header.format.fill=navy;
  header.format.font={name:"Arial",size:10,bold:true,color:"#FFFFFF"};
  header.format.rowHeight=34;
  header.format.wrapText=true;
  header.format.verticalAlignment="center";
  if(data.length){
    const body=sh.getRangeByIndexes(row,0,data.length,n);
    body.format.rowHeight=27;
    body.format.verticalAlignment="center";
  }
}
function base(sh,title,widths={}){
  sh.showGridLines=false;
  sh.getRange("A1:Q48").format.font={name:"Arial",size:10,color:ink};
  cell(sh,"A2",title);
  sh.getRange("A2").format.font={name:"Arial",size:14,bold:true,color:navy};
  sh.getRange("A2").format.rowHeight=31;
  sh.getRange("A3:Q3").format.borders={bottom:{style:"thin",color:"#B9C8D4"}};
  for(const [col,w] of Object.entries({A:26,B:18,C:18,D:18,E:20,F:20,G:20,H:20,I:19,J:18,K:18,...widths}))
    sh.getRange(col+":"+col).format.columnWidth=w;
}
function section(sh,address,title){cell(sh,address,title);sh.getRange(address).format.font={name:"Arial",size:11,bold:true,color:blue}}
function note(sh,address,text,width=70,height=48){
  cell(sh,address,text);
  const range=sh.getRange(address);
  range.format.wrapText=true;
  range.format.rowHeight=height;
  range.format.columnWidth=width;
  range.format.verticalAlignment="center";
}

// Owning build: all general cost formulas live on Model_Cost.
{
 const sh=sheets.Model_Cost;
 base(sh,"Full-battery cost-to-serve and Claude observed economics",{A:30,B:14,C:14,D:16,E:21,F:21,G:23,H:21,I:22,J:15,K:15});
 cell(sh,"A4","Monthly referral scenario");cell(sh,"B4",4000);
 cell(sh,"A5","Nurse USD / hour");cell(sh,"B5",55);
 cell(sh,"A6","Minutes / failed referral");cell(sh,"B6",10);
 cell(sh,"A7","Fixed USD / month");cell(sh,"B7",0);
 sh.getRange("B4:B7").format.fill=amber;
 section(sh,"A9","A. Four V2 full-battery models (52 scored runs each)");
 rows(sh,10,["Model","Passed","Runs","Pass rate","Provider spend USD","AI USD/ref","Fallback USD/ref","Total USD/ref","Monthly USD","Invalid","Unsafe"],
      full.map((s,i)=>[labels[i],s.passed_runs,s.runs,null,s.provider_spend_usd,null,null,null,null,s.invalid_model_output_count,s.unsafe_action_count]));
 for(let i=0;i<4;i++){
   const r=11+i;
   formula(sh,"D"+r,`=B${r}/C${r}`);
   formula(sh,"F"+r,`=E${r}/C${r}`);
   formula(sh,"G"+r,`=(1-D${r})*$B$5*$B$6/60`);
   formula(sh,"H"+r,`=F${r}+G${r}`);
   formula(sh,"I"+r,`=H${r}*$B$4+$B$7`);
 }
 sh.getRange("D11:D14").setNumberFormat("0.00%");
 sh.getRange("E11:H14").setNumberFormat(money6);
 sh.getRange("I11:I14").setNumberFormat(monthly);
 section(sh,"A17","Case-balanced: equal weight to each of 40 cases");
 rows(sh,18,["Model","Case coverage","Case pass","Case AI USD/ref","Fallback USD/ref","Total USD/ref","Monthly USD","AI cost cases"],
      full.map((s,i)=>[labels[i],"40/40",s.case_balanced_pass_rate,s.case_balanced_ai_cost_per_referral,null,null,null,s.case_balanced_provider_cost_case_coverage]));
 for(let i=0;i<4;i++){
   const r=19+i;
   formula(sh,"E"+r,`=(1-C${r})*$B$5*$B$6/60`);
   formula(sh,"F"+r,`=D${r}+E${r}`);
   formula(sh,"G"+r,`=F${r}*$B$4+$B$7`);
 }
 sh.getRange("C19:C22").setNumberFormat("0.00%");
 sh.getRange("D19:F22").setNumberFormat(money6);
 sh.getRange("G19:G22").setNumberFormat(monthly);
 sh.getRange("G18:G22").format.borders={right:{style:"thin",color:"#DCE5EB"}};
 section(sh,"A25","B. Claude Opus 5 - Frontier negative-only (not general production)");
 rows(sh,26,["Model","Passed","Negative trials","Negative pass","Invalid","Unsafe","Provider spend USD","Mean AI USD/run"],
      [["Claude Opus 5",10,18,null,8,0,claude.provider_spend_usd,null]]);
 formula(sh,"D27","=B27/C27");
 formula(sh,"H27","=G27/C27");
 sh.getRange("D27").setNumberFormat("0.00%");
 sh.getRange("G27:H27").setNumberFormat(money6);
 note(sh,"A29","Overall/full-battery pass and general monthly, sensitivity, break-even, Pareto: N/A - NEGATIVE_ONLY_SCOPE. Six negative cases x three trials. No extrapolation to 4,000 referrals.",94,55);
}

{
 const sh=sheets.Executive_Summary;
 base(sh,"Problem B - D6 cost summary",{A:27,B:20,C:18,D:22,E:22,F:35});
 section(sh,"A5","Problem B assumptions");
 rows(sh,6,["Monthly referrals","Nurse USD/hour","Minutes/failure","Failure USD","Fixed USD/month","Fixed-cost status"],
      [[4000,55,10,55*10/60,0,"Baseline assumption; not measured"]]);
 sh.getRange("D7").setNumberFormat(money6);
 sh.getRange("F7").format.wrapText=true;
 sh.getRange("F7").format.rowHeight=45;
 section(sh,"A10","Four full-battery V2 monthly scenarios");
 rows(sh,11,["Model","Pass / 52","Pass rate","AI USD/ref","Fallback USD/ref","Monthly USD"],
      full.map((s,i)=>[labels[i],`${s.passed_runs}/${s.runs}`,null,null,null,null]));
 for(let i=0;i<4;i++){
   const r=12+i,m=11+i;
   formula(sh,"C"+r,`='Model_Cost'!D${m}`);
   formula(sh,"D"+r,`='Model_Cost'!F${m}`);
   formula(sh,"E"+r,`='Model_Cost'!G${m}`);
   formula(sh,"F"+r,`='Model_Cost'!I${m}`);
 }
 sh.getRange("C12:C15").setNumberFormat("0.00%");
 sh.getRange("D12:E15").setNumberFormat(money6);
 sh.getRange("F12:F15").setNumberFormat(monthly);
 section(sh,"A18","Prompt control and evaluation charges");
 cell(sh,"A19","Qwen V1 -> V2");cell(sh,"B19","20/52 -> 28/52");cell(sh,"C19","+15.38 pp");
 cell(sh,"A20","Selected scored-run spend");cell(sh,"B20",report.evaluation_spend.selected_scored_run_spend);
 cell(sh,"A21","Extra charged provider error");cell(sh,"B21",report.evaluation_spend.extra_charged_mistral_provider_error);
 sh.getRange("B20:B21").setNumberFormat(money);
 section(sh,"A24","Frontier negative-only and tier context");
 note(sh,"A25","Claude Opus 5: 10/18 negative pass, 18/18 provider costs, USD 1.644405 spend. No overall pass or general monthly scenario.",88,50);
 note(sh,"A27","Team tiers: GPT / Qwen / Mistral / Gemini lower-price; Claude Frontier. Five distinct families: OpenAI, Qwen, Mistral, Google, Anthropic. Exact-model tier mapping is not asserted as official.",88,55);
}

{
 const sh=sheets.Prompt_Impact; base(sh,"Qwen V1 to V2 matched prompt control",{A:29,B:20,C:20,D:21});
 rows(sh,5,["Metric","V1","V2","V2 minus V1"],[
  ["Pass / 52","20/52","28/52","+8/52 = +15.38 pp"],
  ["Invalid / 52","26/52","14/52","-12/52"],
  ["AI USD/ref",report.qwen_prompt_ablation[0].v1_ai_cost_per_referral,report.qwen_prompt_ablation[0].v2_ai_cost_per_referral,report.qwen_prompt_ablation[0].delta_ai_cost_per_referral],
  ["Fallback USD/ref",report.qwen_prompt_ablation[0].v1_fallback_cost_per_referral,report.qwen_prompt_ablation[0].v2_fallback_cost_per_referral,report.qwen_prompt_ablation[0].delta_fallback_cost_per_referral],
  ["Monthly USD",report.qwen_prompt_ablation[0].v1_monthly_scenario,report.qwen_prompt_ablation[0].v2_monthly_scenario,report.qwen_prompt_ablation[0].delta_monthly_cost],
  ["Case-balanced monthly USD",report.qwen_prompt_ablation[1].v1_monthly_scenario,report.qwen_prompt_ablation[1].v2_monthly_scenario,report.qwen_prompt_ablation[1].delta_monthly_cost],
 ]);
 sh.getRange("B8:D9").setNumberFormat(money6);
 sh.getRange("B10:D11").setNumberFormat(monthly);
 note(sh,"A14","The fallback change is success-only under the nurse-time assumption; the total monthly difference also includes AI execution cost. Case-balanced metrics average within case before averaging cases.",95,64);
}

{
 const sh=sheets.Evaluation_Spend; base(sh,"Recorded evaluation charges and budget context",{A:40,B:25,C:75});
 rows(sh,5,["Component","USD","Scope"],[
  ["Selected scored runs (278/278)",report.evaluation_spend.selected_scored_run_spend,"Current selected 5+1; provider-recorded"],
  ["Extra charged Mistral provider error",report.evaluation_spend.extra_charged_mistral_provider_error,"Not a scored trial"],
  ["Recorded charges including error",null,"Scored runs plus extra call"],
  ["Historical account increment",.653968992,"Superseded selection/time; not reconciled"],
  ["Historical account residual",.018762122,"Superseded selection/time; unattributed"],
 ]);
 formula(sh,"B8","=SUM(B6:B7)");
 sh.getRange("B6:B10").setNumberFormat(money);
 note(sh,"A13","The local official PDF Section 7 says USD 10 per personal key for the whole course and permits Frontier negative-only comparison. Its 56-run examples are approximately USD 0.31 / 3.15 / 15.74.",90,60);
 note(sh,"A15","Latest user-supplied updated reference gives USD 0.27 / 2.76 / 13.78 for a 56-run battery, but its revised official PDF was not available locally. Neither reference is the measured mixed-scope final spend. USD 2 is not an evidenced overall assignment cap.",90,72);
}

{
 const sh=sheets.Sensitivity; base(sh,"Success-rate sensitivity - full batteries only",{A:24,B:13,C:18,D:20,E:22,F:22});
 rows(sh,5,["Model","Scenario","Pass rate","AI USD/ref","Fallback USD/ref","Monthly USD"],
      report.sensitivity.map(s=>[labels[full.findIndex(x=>x.experiment_id===s.experiment_id)],s.scenario,s.scenario_pass_rate,s.ai_cost_per_referral,s.fallback_cost_per_referral,s.monthly_variable_cost]));
 sh.getRange("C6:C17").setNumberFormat("0.00%");
 sh.getRange("D6:E17").setNumberFormat(money6);
 sh.getRange("F6:F17").setNumberFormat(monthly);
 note(sh,"A20","LOW / BASE / HIGH change success by ±10 percentage points (not relative percent), clamped to [0,1]. AI execution cost is fixed. Claude has N/A general sensitivity.",92,57);
}

{
 const sh=sheets.Break_Even; base(sh,"Pairwise break-even - four full-battery V2 models",{A:24,B:24,C:20,D:20,E:20});
 rows(sh,5,["Candidate","Benchmark","Raw success threshold","Feasible [0,1]","Measured margin pp"],
      report.break_even_pairs.map(p=>[
        labels[full.findIndex(x=>x.experiment_id===p.candidate_experiment_id)],
        labels[full.findIndex(x=>x.experiment_id===p.benchmark_experiment_id)],
        p.raw_break_even_success_rate,p.feasible_break_even_success_rate,p.measured_margin_pp]));
 sh.getRange("C6:D17").setNumberFormat("0.00%");
 sh.getRange("E6:E17").setNumberFormat("0.00");
 note(sh,"A20","Candidate required pass = 1 - (benchmark expected total cost - candidate AI cost) / failure cost. No Claude or prompt-control extrapolation.",92,60);
}

{
 const sh=sheets.Uncertainty; base(sh,"Case-cluster bootstrap - evaluation sample only",{A:27,B:23,C:22,D:22,E:22});
 const records=report.bootstrap.filter(x=>x.metric==="monthly_cost");
 rows(sh,5,["Model","Median monthly USD","2.5% USD","97.5% USD","Method"],
      records.map(x=>[labels[full.findIndex(s=>s.experiment_id===x.experiment_id)],x.median,x.p2_5,x.p97_5,"5,000 case clusters; seed 6201"]));
 sh.getRange("B6:D9").setNumberFormat(monthly);
 note(sh,"A12","EVALUATION-SAMPLE UNCERTAINTY ONLY. Each sampled case carries all its trial rows. These intervals do not establish hospital prevalence or uncertainty for Claude ordinary cases.",92,65);
}

{
 const sh=sheets.Cost_Levers; base(sh,"B / T / D / S cost-lever evidence",{A:22,B:22,C:26,D:35});
 rows(sh,5,["Lever","Evidence source","Causal status","Interpretation"],
      report.cost_levers.map(x=>[x.lever,x.source,
        x.lever.startsWith("T_")?"Measured within D2":x.lever.startsWith("S_")?"Assumption translation":"Not causally isolated",
        x.reason]));
 sh.getRange("B6:D9").format.wrapText=true;
 sh.getRange("A6:D9").format.rowHeight=85;
 note(sh,"A12","B and D use offline lexical units, NOT_PROVIDER_TOKENIZATION. T is a separate matched D2 control. S is Qwen V1 to V2; fallback is an assumption-based translation, not measured nurse spend.",94,70);
}

{
 const sh=sheets.Safety_Reliability; base(sh,"Five-model common-negative safety and reliability",{A:29,B:18,C:18,D:21,E:25});
 rows(sh,5,["V2 model","Pass / 18","Invalid / 18","Unsafe book attempts","Provider spend USD"],
      report.common_negative.map((x,i)=>[[...labels,"Claude Opus 5"][i],
        `${x.passed}/18 = ${(x.pass_rate*100).toFixed(2)}%`,
        `${x.invalid_model_output}/18`,x.unsafe_booking_attempts,x.provider_spend_usd]));
 sh.getRange("E6:E10").setNumberFormat(money);
 note(sh,"A13","Identical 18 case/trial keys, six negative cases x three trials. Unsafe means attempted book_slot in a negative case, not necessarily completed booking. This is a stress test, not a general monthly forecast.",92,72);
}

{
 const sh=sheets.Cost_Guardrails; base(sh,"Actual controls and proposed monitoring",{A:30,B:28,C:32,D:64});
 rows(sh,5,["Control","Evidence / value","Status","Interpretation"],[
  ["Step cap","8 turns","Implemented","Frozen D5 config and Agent guardrail core"],
  ["Evaluation budget","Per-battery CLI parameter","Implemented in D5 runner","Not a production agent budget ceiling"],
  ["Monthly per-user limit","No value in saved evidence","Not implemented","Requires an explicit user allocation policy; 4,000 is workload volume"],
  ["Abnormal token/cost","Within-model p95 + headroom","Proposed / monitor-only","No proposed alert was retrospectively applied to D5"],
  ["Action and autonomy","Booking gate; confirm mode","Implemented context","Keep safety separate from dollars"],
 ]);
 sh.getRange("B6:D10").format.wrapText=true;sh.getRange("A6:D10").format.rowHeight=65;
}

{
 const sh=sheets.Methodology_Limits; base(sh,"Scope, provenance and interpretation limits",{A:105});
 const lines=[
  "Evaluation pass rates and 4,000-referral monthly scenarios are not hospital prevalence or production forecasts.",
  "Claude is Frontier negative-only: 18 trials, six negative cases; no ordinary/full-battery pass or general monthly extrapolation.",
  "Four full batteries have 40 cases and six negative cases, giving 52 runs rather than the later expected 40 / eight / 56 shape.",
  "Claude source commit is recorded, but a complete source-tree diff is unavailable locally.",
  "Fixed deployment cost of USD 0 is a baseline assumption, not measured deployment spend.",
  "Historical account snapshots cannot be reconciled to the final selected 5+1 provider charges.",
  "The lower-price / Frontier classification is the team's selection, not an official exact-model tier mapping.",
  "B/D lexical reference units are not provider tokenization. D2 controls are separate from the D5 battery.",
  "The local Section 7 PDF and user-supplied updated 56-run figures differ; the latter cannot be independently verified from a revised local official PDF.",
  "Safety has no sourced monetary penalty. Negative-subset comparisons are stress tests, not production scenarios."
 ];
 lines.forEach((text,i)=>{cell(sh,"A"+(5+i),text);sh.getRange("A"+(5+i)).format.rowHeight=42;sh.getRange("A"+(5+i)).format.wrapText=true});
}

wb.recalculate();
const inspect=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:30},maxChars:4000});
if(inspect.ndjson.includes("#REF!")||inspect.ndjson.includes("#DIV/0!")||inspect.ndjson.includes("#VALUE!"))
  throw new Error("Workbook formula error: "+inspect.ndjson);
const previewDir=path.join(os.tmpdir(),"d6_teacher_workbook_previews");
await fs.mkdir(previewDir,{recursive:true});
const previewRanges={Executive_Summary:"A1:F29",Model_Cost:"A1:K29",Prompt_Impact:"A1:D15",
  Evaluation_Spend:"A1:C16",Sensitivity:"A1:F21",Break_Even:"A1:E21",Uncertainty:"A1:E13",
  Cost_Levers:"A1:D13",Safety_Reliability:"A1:E14",Cost_Guardrails:"A1:D11",Methodology_Limits:"A1:A15"};
for(const name of names){
  const preview=await wb.render({sheetName:name,range:previewRanges[name],scale:1,format:"png"});
  await fs.writeFile(path.join(previewDir,name+".png"),new Uint8Array(await preview.arrayBuffer()));
}
const outputDir=path.join(root,"submission");
await fs.mkdir(outputDir,{recursive:true});
const output=await SpreadsheetFile.exportXlsx(wb);
const target=path.join(outputDir,"PE6201_D6_Cost_Analysis_Teacher_Submission_FIXED.xlsx");
await output.save(target);
console.log(JSON.stringify({target,previewDir,sheets:names}));
