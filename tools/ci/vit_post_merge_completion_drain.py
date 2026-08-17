#!/usr/bin/env python3
from __future__ import annotations

import argparse,json,os,subprocess
from pathlib import Path
from typing import Any,Mapping
from ovc.development.skills.vit_completion_closeout import persist_non_churning_completion_closeout
from ovc.development.skills.vit_materialisation import ReceiptStore
from ovc_evidence_store.external_root import resolve_external_root
from tools.ci.vit_post_merge_completion import PostMergeCompletionError,run as complete_one

class CompletionDrainError(RuntimeError): pass

def _git(repo:Path,*args:str)->str:
    p=subprocess.run(["git","-C",str(repo),*args],check=False,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise CompletionDrainError(p.stderr.strip() or "git command failed")
    return p.stdout.strip()

def _first_parent_commits(repo:Path,head:str,limit:int)->list[str]:
    if limit<1: raise CompletionDrainError("drain limit must be positive")
    resolved=_git(repo,"rev-parse",head)
    rows=[x for x in _git(repo,"rev-list","--first-parent",f"--max-count={limit}",resolved).splitlines() if x.strip()]
    rows.reverse(); return rows

def _lawful_historical_skip(exc:BaseException)->str|None:
    text=str(exc)
    if "expected exactly one merged main PR" in text and "found 0" in text: return "NO_ASSOCIATED_MAIN_PR"
    if "expected one pre-write transaction freeze" in text and "found 0" in text: return "HISTORICAL_PREWRITE_FREEZE_ABSENT"
    return None

def drain(repo_root:Path,head:str,*,limit:int=16)->Mapping[str,Any]:
    external_root=resolve_external_root(repository_root=repo_root,environ=os.environ,create=False)
    store=ReceiptStore(external_root/"receipts"); completed=[]; skipped=[]
    for merge_sha in _first_parent_commits(repo_root,head,limit):
        try: proof=complete_one(repo_root,merge_sha)
        except PostMergeCompletionError as exc:
            reason=_lawful_historical_skip(exc)
            if reason is None: raise
            skipped.append({"merge_sha":merge_sha,"reason":reason}); continue
        closeout=persist_non_churning_completion_closeout(receipt_store=store,proof=proof)
        completed.append({"merge_sha":merge_sha,"transaction_id":proof["transaction_id"],"completion_state_id":closeout["completion_state_id"],"packet_id":closeout["packet_id"],"status":closeout["status"],"successor_release_status":closeout["successor_release_status"],"ordinary_closeout_pr_required":False})
    summary={"schema":"ovc-vit-post-merge-completion-drain/v1","head":_git(repo_root,"rev-parse",head),"first_parent_limit":int(limit),"completed_or_reaffirmed":completed,"historical_skips":skipped,"physical_write_repeated":False,"ordinary_closeout_pr_required":False,"authority_effect":"NONE"}
    print("OVC_VIT_POST_MERGE_COMPLETION_DRAIN "+json.dumps(summary,sort_keys=True)); return summary

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--repo-root",default="."); p.add_argument("--head",required=True); p.add_argument("--limit",type=int,default=16); a=p.parse_args()
    try: drain(Path(a.repo_root).resolve(),a.head,limit=a.limit); return 0
    except Exception as exc:
        print(f"::error title=DSAI3V completion drain failed::OVC_VIT_POST_MERGE_COMPLETION_DRAIN_FAILED: {exc}",flush=True); return 1

if __name__=="__main__": raise SystemExit(main())
