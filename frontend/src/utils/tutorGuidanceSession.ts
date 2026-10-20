import type { TutorGuidancePayload, TutorGuidanceResult } from '../api/agentService'

/** Owns async identity, retry snapshots and the last confirmed displayed turn. */
export class TutorGuidanceSession {
  epoch = 0
  previousRequestId: string | undefined
  pending: TutorGuidancePayload | undefined
  latest: TutorGuidanceResult | undefined
  latestPayload: TutorGuidancePayload | undefined

  reset() {
    this.epoch += 1
    this.previousRequestId = undefined
    this.pending = undefined
    this.latest = undefined
    this.latestPayload = undefined
  }

  start(payload: TutorGuidancePayload) {
    this.epoch += 1
    this.pending = structuredClone(payload)
    return { epoch: this.epoch, payload: structuredClone(this.pending) }
  }

  retry() {
    return this.pending ? this.start(this.pending) : undefined
  }

  accept(epoch: number, result: TutorGuidanceResult) {
    if (epoch !== this.epoch) return false
    this.latest = result
    this.latestPayload = this.pending ? structuredClone(this.pending) : undefined
    this.pending = undefined
    return true
  }

  confirm(epoch: number, requestId: string) {
    if (epoch !== this.epoch || this.latest?.requestId !== requestId) return false
    this.previousRequestId = requestId
    return true
  }
}
