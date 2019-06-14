# Example Postmortem

## Shakespeare Sonnet++ Postmortem (incident #465)

**Date**: 2015-10-21

**Authors**: jennifer, martym, agoogler

**Status**: Complete, action items in progress

## Summary:

Shakespeare Search down for 66 minutes during period of very high interest in Shakespeare due to discovery of a new sonnet.

## Impact:163 Estimated 1.21B queries lost, no revenue impact.

## Root Causes:164

Cascading failure due to combination of exceptionally high load and a resource leak when searches failed due to terms not being in the Shakespeare corpus. The newly discovered sonnet used a word that had never before appeared in one of Shakespeare’s works, which happened to be the term users searched for. Under normal circumstances, the rate of task failures due to resource leaks is low enough to be unnoticed.

### Trigger: Latent bug triggered by sudden increase in traffic.

**Detection**: Borgmon detected high level of HTTP 500s and paged on-call.

### Resolution:

Directed traffic to sacrificial cluster and added 10x capacity to mitigate cascading failure. Updated index deployed, resolving interaction with latent bug. Maintaining extra capacity until surge in public interest in new sonnet passes. Resource leak identified and fix deployed.

Action Items:165

|Action Item |Type |Owner |Bug|
|------------|---- |----- |---|
|Update playbook with instructions for responding to cascading failure| mitigate |jennifer| n/a DONE|
|Use flux capacitor to balance load between clusters|prevent|martym|Bug 5554823 TODO|
|Schedule cascading failure test during next DiRT|process|docbrown|n/a TODO|
|Investigate running index MR/fusion continuously|prevent|jennifer|Bug 5554824 TODO|
|Plug file descriptor leak in search ranking subsystem|prevent

## Lessons Learned
### What went well

Monitoring quickly alerted us to high rate (reaching ~100%) of HTTP 500s
Rapidly distributed updated Shakespeare corpus to all clusters
### What went wrong

We’re out of practice in responding to cascading failure
We exceeded our availability error budget (by several orders of magnitude) due to the exceptional surge of traffic that essentially all resulted in failures
### Where we got lucky [166](#166)

Mailing list of Shakespeare aficionados had a copy of new sonnet available
Server logs had stack traces pointing to file descriptor exhaustion as cause for crash
Query-of-death was resolved by pushing new index containing popular search term

## Timeline167
2015-10-21 (all times UTC)

- 14:51 News reports that a new Shakespearean sonnet has been discovered in a Delorean’s glove compartment
- 14:53 Traffic to Shakespeare search increases by 88x after post to /r/shakespeare points to Shakespeare search engine as place to find new sonnet (except we don’t have the sonnet yet)
- 14:54 OUTAGE BEGINS — Search backends start melting down under load
- 14:55 docbrown receives pager storm, ManyHttp500s from all clusters
- 14:57 All traffic to Shakespeare search is failing: see http://monitor
- 14:58 docbrown starts investigating, finds backend crash rate very high
- 15:01 INCIDENT BEGINS docbrown declares incident #465 due to cascading failure, coordination on #shakespeare, names jennifer incident commander
- 15:02 someone coincidentally sends email to shakespeare-discuss@ re sonnet discovery, which happens to be at top of martym’s inbox

- 16:30 **INCIDENT ENDS**, reached exit criterion of 30 minutes’ nominal performance

## Supporting information:
[Monitoring dashboard,](http://monitor/shakespeare?end_time=20151021T160000&duration=7200)

163 Impact is the effect on users, revenue, etc.

166 <a name="166"></a>This section is really for near misses, e.g., “The goat teleporter was available for emergency use with other animals despite lack of certification.”