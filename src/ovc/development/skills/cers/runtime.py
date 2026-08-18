from __future__ import annotations
from dataclasses import replace
from typing import Iterable, Mapping
from .model import DispatchIdentity,DispatchTransaction,ExecutorCapabilityRecord,QuiescenceControl,SupervisorLease,WorkerOwnership

class LeaseManager:
    def __init__(self): self._epochs={}; self._leases={}
    def acquire(self,scope,holder_identity):
        epoch=self._epochs.get(scope,0)+1; self._epochs[scope]=epoch; lease=SupervisorLease(scope,holder_identity,epoch); self._leases[scope]=lease; return lease
    def validate(self,lease):
        current=self._leases.get(lease.scope); return bool(current and current.active and current.lease_id==lease.lease_id and current.fencing_generation==self._epochs.get(lease.scope))
    def release(self,lease):
        if self.validate(lease): self._leases[lease.scope]=replace(lease,active=False)

class EventLedger:
    def __init__(self): self._events={}
    def ingest(self,*,source,source_sequence,event):
        key=(source,source_sequence); previous=self._events.get(key)
        if previous is not None:
            if dict(previous)!=dict(event): raise ValueError("EVENT_IDENTITY_CONFLICT")
            return False
        self._events[key]=dict(event); return True
    def ordered(self): return tuple(self._events[k] for k in sorted(self._events))

class FixtureExecutor:
    def __init__(self,executor_id="CERS_FIXTURE_EXECUTOR_V0_1"):
        self.capability=ExecutorCapabilityRecord(executor_id,False,False,False,False,False,("BUILD_FIXTURE_SUCCESSOR","RECONCILE_FIXTURE","RUN_FIXTURE_TEST"),"CERS_SYNTHETIC_NON_WRITING_V0_1")
        self.starts={}; self.outcomes={}
    def start(self,identity,lease,quiescence):
        if quiescence.blocks_new_dispatch: raise PermissionError("QUIESCENCE_BLOCKS_NEW_DISPATCH")
        if identity.executor_id!=self.capability.executor_id: raise PermissionError("EXECUTOR_IDENTITY_MISMATCH")
        if identity.fencing_generation!=lease.fencing_generation: raise PermissionError("STALE_FENCE")
        if identity.dispatch_id in self.starts: return self.starts[identity.dispatch_id]
        worker=WorkerOwnership(identity.dispatch_id,f"fixture-{identity.dispatch_id[:16]}",self.capability.executor_id,lease.fencing_generation,1)
        self.starts[identity.dispatch_id]=worker; self.outcomes[identity.dispatch_id]=DispatchTransaction(identity.dispatch_id,"START_ACKNOWLEDGED",lease.fencing_generation,worker.worker_run_id); return worker
    def heartbeat(self,dispatch_id,fencing_generation):
        worker=self.starts[dispatch_id]
        if worker.fencing_generation!=fencing_generation: raise PermissionError("STALE_FENCE")
        worker=replace(worker,heartbeat_sequence=worker.heartbeat_sequence+1); self.starts[dispatch_id]=worker; return worker
    def complete(self,dispatch_id,fencing_generation,*,success=True):
        worker=self.starts[dispatch_id]
        if worker.fencing_generation!=fencing_generation or not worker.authoritative: raise PermissionError("STALE_WORKER_COMPLETION")
        result=DispatchTransaction(dispatch_id,"COMPLETED" if success else "FAILED",fencing_generation,worker.worker_run_id); self.outcomes[dispatch_id]=result; return result

class DispatchCoordinator:
    def __init__(self,lease_manager,executor): self.lease_manager=lease_manager; self.executor=executor; self.transactions={}
    def dispatch(self,identity,lease,quiescence):
        if not self.lease_manager.validate(lease): raise PermissionError("STALE_FENCE")
        if not self.executor.capability.non_writing_fixture_only: raise PermissionError("LIVE_WRITE_CAPABILITY_NOT_AUTHORISED")
        existing=self.transactions.get(identity.dispatch_id)
        if existing and existing.phase in {"START_ACKNOWLEDGED","RUNNING","COMPLETED","FAILED","CANCELLED"}: return existing
        self.transactions[identity.dispatch_id]=DispatchTransaction(identity.dispatch_id,"INTENT_PERSISTED",lease.fencing_generation)
        worker=self.executor.start(identity,lease,quiescence); tx=DispatchTransaction(identity.dispatch_id,"START_ACKNOWLEDGED",lease.fencing_generation,worker.worker_run_id); self.transactions[identity.dispatch_id]=tx; return tx
    def mark_unknown_start(self,identity,lease):
        if not self.lease_manager.validate(lease): raise PermissionError("STALE_FENCE")
        tx=DispatchTransaction(identity.dispatch_id,"DISPATCH_UNKNOWN",lease.fencing_generation,reason="UNKNOWN_START_STATE"); self.transactions[identity.dispatch_id]=tx; return tx
    def reconcile_unknown(self,dispatch_id):
        current=self.transactions[dispatch_id]
        if current.phase!="DISPATCH_UNKNOWN": return current
        observed=self.executor.outcomes.get(dispatch_id)
        if observed is None: return current
        self.transactions[dispatch_id]=observed; return observed

def selective_invalidation(*,changed_dependency:str,descendants:Iterable[Mapping[str,object]]):
    return tuple(sorted(str(r["packet_id"]) for r in descendants if changed_dependency in set(map(str,r.get("dependencies",())))))
def failure_route(programme_id,packet_id): return {"programme_id":programme_id,"packet_id":packet_id,"route":"EXISTING_PROGRAMME_REPAIR_OWNER","cers_remediation_authority":"NONE"}
