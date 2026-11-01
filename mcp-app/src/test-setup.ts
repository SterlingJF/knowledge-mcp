// The card lifecycle remembers frozen cards in localStorage; each test starts with none.
afterEach(() => {
  try {
    localStorage.clear();
  } catch {
    // No storage in this environment.
  }
});
