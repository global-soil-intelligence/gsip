import { configure } from '@testing-library/react'

// On a busy machine the app's first render, with its IndexedDB reads, can take longer than
// Testing Library's one-second default wait. A longer wait only delays a test that fails anyway.
configure({ asyncUtilTimeout: 5_000 })
