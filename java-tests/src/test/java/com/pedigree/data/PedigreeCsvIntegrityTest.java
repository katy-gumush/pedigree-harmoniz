package com.pedigree.data;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.io.InputStreamReader;
import java.io.Reader;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Data-level pedigree integrity tests.
 *
 * <p>Load CSV records directly from the classpath (no running server required).
 * Structural rules: required fields, unique IDs, valid parent references,
 * no self-parenting, no directed cycle in parent links (any length, DFS),
 * and non-negative measurements.
 *
 * <p>Fixtures under {@code /fixtures/} are small CSVs (few rows each) produced by
 * {@code scripts/generate_corrupted_datasets.py}: clean, bad parent id, duplicate id,
 * immediate two-node cycle, and a three-node sire-only cycle.
 */
@Tag("data")
class PedigreeCsvIntegrityTest {

    private static final String FIXTURES = "/fixtures/";

    @Test
    @DisplayName("clean CSV passes all integrity rules")
    void cleanCsvPassesAll() {
        List<CSVRecord> rows = loadCsv("clean.csv");
        assertRequiredFields(rows, true);
        assertUniqueIds(rows, true);
        assertParentReferencesValid(rows, true);
        assertNoSelfParent(rows, true);
        assertNoDirectedParentCycle(rows, true);
        assertNonNegativeMeasurements(rows, true);
    }

    @Test
    @DisplayName("corrupt_bad_parent_id.csv fails parent-reference check (sire_id 9999 is unknown)")
    void badParentIdFailsParentRefCheck() {
        List<CSVRecord> rows = loadCsv("corrupt_bad_parent_id.csv");
        assertRequiredFields(rows, true);
        assertUniqueIds(rows, true);
        assertNoSelfParent(rows, true);
        assertNoDirectedParentCycle(rows, true);
        assertParentReferencesValid(rows, false);
    }

    @Test
    @DisplayName("corrupt_duplicate_id.csv fails unique-ID check (ID 1 appears twice)")
    void duplicateIdFailsUniquenessCheck() {
        List<CSVRecord> rows = loadCsv("corrupt_duplicate_id.csv");
        assertRequiredFields(rows, true);
        assertParentReferencesValid(rows, true);
        assertNoSelfParent(rows, true);
        assertUniqueIds(rows, false);
    }

    @Test
    @DisplayName("corrupt_immediate_loop.csv fails directed cycle check (two-dog mutual parent links)")
    void immediateLoopFailsDirectedCycleCheck() {
        List<CSVRecord> rows = loadCsv("corrupt_immediate_loop.csv");
        assertRequiredFields(rows, true);
        assertUniqueIds(rows, true);
        assertNoSelfParent(rows, true);
        assertNoDirectedParentCycle(rows, false);
    }

    @Test
    @DisplayName("corrupt_long_cycle.csv fails directed cycle check (3-node sire-only loop)")
    void longCycleFailsDirectedCycleCheck() {
        List<CSVRecord> rows = loadCsv("corrupt_long_cycle.csv");
        assertRequiredFields(rows, true);
        assertUniqueIds(rows, true);
        assertParentReferencesValid(rows, true);
        assertNoSelfParent(rows, true);
        assertNoDirectedParentCycle(rows, false);
    }

    private void assertRequiredFields(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "Required fields", () -> {
            List<String> violations = new ArrayList<>();
            for (CSVRecord row : rows) {
                for (String field : List.of("ID", "Name", "Breed", "Sex")) {
                    if (row.get(field).isBlank()) {
                        violations.add("Row " + row.getRecordNumber() + ": blank field '" + field + "'");
                    }
                }
            }
            assertTrue(violations.isEmpty(), "Required-field violations:\n" + String.join("\n", violations));
        });
    }

    private void assertUniqueIds(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "Unique IDs", () -> {
            Map<String, Long> counts = new LinkedHashMap<>();
            for (CSVRecord row : rows) {
                counts.merge(row.get("ID"), 1L, Long::sum);
            }
            List<String> duplicates = new ArrayList<>();
            counts.forEach((id, count) -> {
                if (count > 1) duplicates.add("ID " + id + " appears " + count + " times");
            });
            assertTrue(duplicates.isEmpty(), "Duplicate IDs:\n" + String.join("\n", duplicates));
        });
    }

    private void assertParentReferencesValid(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "Valid parent references", () -> {
            Set<String> ids = new HashSet<>();
            for (CSVRecord row : rows) ids.add(row.get("ID"));

            List<String> violations = new ArrayList<>();
            for (CSVRecord row : rows) {
                for (String field : List.of("Sire_ID", "Dam_ID")) {
                    String ref = row.get(field).strip();
                    if (!ref.isEmpty() && !ids.contains(ref)) {
                        violations.add("Dog " + row.get("ID") + " (" + row.get("Name") + "): "
                                + field + " " + ref + " does not reference an existing dog");
                    }
                }
            }
            assertTrue(violations.isEmpty(), "Broken parent references:\n" + String.join("\n", violations));
        });
    }

    private void assertNoSelfParent(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "No self-parenting", () -> {
            List<String> violations = new ArrayList<>();
            for (CSVRecord row : rows) {
                String id = row.get("ID");
                for (String field : List.of("Sire_ID", "Dam_ID")) {
                    if (id.equals(row.get(field).strip())) {
                        violations.add("Dog " + id + " lists itself as " + field);
                    }
                }
            }
            assertTrue(violations.isEmpty(), "Self-parenting violations:\n" + String.join("\n", violations));
        });
    }

    /**
     * Follow each dog's sire/dam links as directed edges (child → parent). Any directed
     * cycle (length ≥ 2) makes the pedigree inconsistent; a two-node swap is only one case.
     */
    private void assertNoDirectedParentCycle(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "No directed cycle in parent links", () -> {
            Set<String> allIds = new HashSet<>();
            for (CSVRecord row : rows) {
                allIds.add(row.get("ID").strip());
            }
            Map<String, List<String>> childToParents = new HashMap<>();
            for (CSVRecord row : rows) {
                String id = row.get("ID").strip();
                List<String> parents = new ArrayList<>();
                for (String field : List.of("Sire_ID", "Dam_ID")) {
                    String p = row.get(field).strip();
                    if (!p.isEmpty() && allIds.contains(p)) {
                        parents.add(p);
                    }
                }
                childToParents.put(id, parents);
            }
            Map<String, VisitState> state = new HashMap<>();
            for (String id : allIds) {
                state.put(id, VisitState.UNSEEN);
            }
            List<String> violations = new ArrayList<>();
            for (String id : allIds) {
                if (state.get(id) == VisitState.UNSEEN) {
                    dfsParentCycle(id, childToParents, state, violations);
                }
            }
            assertTrue(violations.isEmpty(),
                    "Directed cycles in parent links:\n" + String.join("\n", violations));
        });
    }

    private enum VisitState {
        UNSEEN, ACTIVE, DONE
    }

    private void dfsParentCycle(
            String u,
            Map<String, List<String>> childToParents,
            Map<String, VisitState> state,
            List<String> violations
    ) {
        state.put(u, VisitState.ACTIVE);
        for (String p : childToParents.getOrDefault(u, List.of())) {
            VisitState ps = state.get(p);
            if (ps == VisitState.ACTIVE) {
                violations.add("Dog " + u + " reaches dog " + p + " again on the same ancestor walk (cycle)");
            } else if (ps == VisitState.UNSEEN) {
                dfsParentCycle(p, childToParents, state, violations);
            }
        }
        state.put(u, VisitState.DONE);
    }

    private void assertNonNegativeMeasurements(List<CSVRecord> rows, boolean expectPass) {
        runRule(expectPass, "Non-negative measurements", () -> {
            List<String> violations = new ArrayList<>();
            for (CSVRecord row : rows) {
                for (String field : List.of("Height_cm", "Weight_kg")) {
                    String val = row.get(field).strip();
                    if (!val.isEmpty()) {
                        double d = Double.parseDouble(val);
                        if (d < 0) {
                            violations.add("Dog " + row.get("ID") + ": " + field + " = " + d);
                        }
                    }
                }
            }
            assertTrue(violations.isEmpty(), "Negative measurements:\n" + String.join("\n", violations));
        });
    }

    private void runRule(boolean expectPass, String ruleName, ThrowingRunnable rule) {
        if (expectPass) {
            assertDoesNotThrow(rule::run, "Rule '" + ruleName + "' should pass but threw");
        } else {
            AssertionError error = assertThrows(AssertionError.class, rule::run,
                    "Rule '" + ruleName + "' should fail on corrupted data but passed");
            assertFalse(error.getMessage() == null || error.getMessage().isBlank(),
                    "Failure message must not be blank");
        }
    }

    private List<CSVRecord> loadCsv(String filename) {
        try (Reader reader = new InputStreamReader(
                Objects.requireNonNull(
                        getClass().getResourceAsStream(FIXTURES + filename),
                        "Fixture not found on classpath: " + FIXTURES + filename))) {
            return CSVFormat.DEFAULT.builder()
                    .setHeader()
                    .setSkipHeaderRecord(true)
                    .build()
                    .parse(reader)
                    .getRecords();
        } catch (Exception e) {
            throw new RuntimeException("Failed to load fixture " + filename, e);
        }
    }

    @FunctionalInterface
    interface ThrowingRunnable {
        void run() throws Exception;
    }
}
