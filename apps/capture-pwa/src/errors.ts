/** The server refused a queued observation because its contributor withdrew it (SQLSTATE WD001). */
export class RecordWithdrawn extends Error {
  constructor() {
    super('This observation was withdrawn by its contributor.')
    this.name = 'RecordWithdrawn'
  }
}

/**
 * The observation was queued under an account that is no longer signed in on this device (signed
 * out, or deleted). It is never sent under another account without the person's say-so.
 */
export class AccountChanged extends Error {
  constructor() {
    super('This observation belongs to an account that is not signed in here.')
    this.name = 'AccountChanged'
  }
}

export function isWithdrawal(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    (error as { code?: unknown }).code === 'WD001'
  )
}
