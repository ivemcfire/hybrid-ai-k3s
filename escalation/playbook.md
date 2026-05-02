# Manual Escalation Playbook

The local model on the RTX 3060 handles routine work. The cloud model
(Gemini 3.1 Pro) is on call for two specific roles, invoked **manually**.

## When to escalate

### Audit
You have a plan from the local model. It looks reasonable. The change is
risky enough that you want a second opinion before applying it.

Examples that have crossed this bar:
- Anything touching cluster RBAC or service accounts
- StorageClass / PV changes that could lose recordings or DB state
- Network policies that could partition workloads
- Autoscaler thresholds (the local model agreed too easily on a bad
  CPU+memory threshold mix once — that is exactly why audit exists)

### Advisor
You are stuck on a design call where the local model is not strong enough.
You want pushback on framing, not autocomplete.

Examples that have crossed this bar:
- Choosing between two architectural patterns that both "work"
- Capacity planning across heterogeneous nodes
- Trade-offs between availability and cost on a small cluster

## What never escalates

- Drafting a manifest from a known shape
- Recalling a `kubectl` flag
- YAML editing
- Log triage
- Anything routine

If it is routine, it stays local. The point is not to use the cloud less —
the point is to know which questions deserve cloud cycles.

## How to escalate

1. **Sanitise the payload.** Pipe through
   [`scripts/sanitise.sh`](../scripts/sanitise.sh) at minimum. Eyeball
   anything the script might miss.
2. **State the role explicitly.** Open with one of:
   - "Audit this plan. Look for what is wrong, not what is right."
   - "Advise on this design. Push back on my framing."
3. **Include the constraint set.** What cannot change, what must hold,
   what is fixed by the homelab.
4. **Log the call.** Date, role, payload size. Not the contents.

## What to do with the answer

The cloud model's output is **input**, not authority. Read it, push back
on it, apply judgement. The default is still:

> Nothing leaves the network unless I decide it is worth leaving.

And nothing comes back unsupervised either.
