package com.pedigree.ui;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.LoadState;
import org.junit.jupiter.api.*;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * UI-level pedigree tests using Playwright Java.
 *
 * Strategy:
 *   Tests drive a real browser (Chromium, headless by default) against the
 *   running Python app. The base URL is read from the {@code base.url} system
 *   property (default: http://127.0.0.1:8000).
 *
 *   Known dog used as the anchor throughout:
 *     Dog 51 – Henry, Labrador Retriever x French Bulldog
 *       sire: Dog 1  – Max,  Labrador Retriever
 *       dam:  Dog 2  – Lucy, French Bulldog
 *
 *   Flow covered:
 *     1. Dogs list page: table is visible, dog row is present
 *     2. Dog card page: all required fields shown, pedigree link works
 *     3. Pedigree page: root, ancestors, descendants rendered correctly
 *     4. Error state: navigating to a non-existent dog shows an error, not a crash
 *
 * Prerequisites:
 *   Run once before first test execution:
 *     mvn -f java-tests/pom.xml exec:java \
 *       -Dexec.mainClass=com.microsoft.playwright.CLI \
 *       -Dexec.args="install chromium"
 */
@Tag("ui")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class PedigreeUiTest {

    private static final int KNOWN_DOG_ID = 51;
    private static final String KNOWN_DOG_NAME = "Henry";
    private static final String KNOWN_SIRE_NAME = "Max";
    private static final String KNOWN_DAM_NAME = "Lucy";
    private static final int NON_EXISTENT_DOG_ID = 99999;

    private static Playwright playwright;
    private static Browser browser;
    private static String baseUrl;

    private Page page;

    @BeforeAll
    static void launchBrowser() {
        baseUrl = System.getProperty("base.url", "http://127.0.0.1:8000");
        playwright = Playwright.create();
        browser = playwright.chromium().launch(
                new BrowserType.LaunchOptions().setHeadless(true)
        );
    }

    @AfterAll
    static void closeBrowser() {
        browser.close();
        playwright.close();
    }

    @BeforeEach
    void newPage() {
        page = browser.newPage();
    }

    @AfterEach
    void closePage() {
        page.close();
    }

    // ------------------------------------------------------------------
    // Dogs list page
    // ------------------------------------------------------------------

    @Test
    @Order(1)
    @DisplayName("Home page shows the dogs table")
    void homePageShowsDogTable() {
        page.navigate(baseUrl + "/");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        Locator table = page.locator("[data-testid='dog-table']");
        assertTrue(table.isVisible(), "dog-table element should be visible on home page");

        // At least one dog row should be rendered
        List<Locator> rows = page.locator("[data-testid^='dog-row-']").all();
        assertTrue(rows.size() > 100, "Expected >100 dog rows, got " + rows.size());
    }

    @Test
    @Order(2)
    @DisplayName("Dog row for known dog 51 is present in the list")
    void listContainsKnownDog() {
        page.navigate(baseUrl + "/");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        Locator row = page.locator("[data-testid='dog-row-" + KNOWN_DOG_ID + "']");
        assertTrue(row.isVisible(), "Row for dog " + KNOWN_DOG_ID + " should be in the list");
        assertTrue(row.textContent().contains(KNOWN_DOG_NAME),
                "Row should contain dog name '" + KNOWN_DOG_NAME + "'");
    }

    // ------------------------------------------------------------------
    // Dog card page
    // ------------------------------------------------------------------

    @Test
    @Order(3)
    @DisplayName("Dog card for dog 51 shows all required fields")
    void dogCardShowsAllRequiredFields() {
        page.navigate(baseUrl + "/dogs/" + KNOWN_DOG_ID);
        page.waitForLoadState(LoadState.NETWORKIDLE);

        Locator card = page.locator("[data-testid='dog-card']");
        assertTrue(card.isVisible(), "dog-card element should be visible");

        // Each field must be present and non-blank
        String[] testids = {"dog-card-id", "dog-card-name", "dog-card-breed",
                            "dog-card-sex", "dog-card-height", "dog-card-weight"};
        for (String testid : testids) {
            Locator el = page.locator("[data-testid='" + testid + "']");
            assertTrue(el.isVisible(), "Element " + testid + " must be visible");
            assertFalse(el.textContent().isBlank(), "Element " + testid + " must not be blank");
        }

        // Name must be correct
        assertEquals(KNOWN_DOG_NAME, page.locator("[data-testid='dog-card-name']").textContent().strip());
    }

    @Test
    @Order(4)
    @DisplayName("Dog card shows correct parents for dog 51 (Max and Lucy)")
    void dogCardShowsCorrectParents() {
        page.navigate(baseUrl + "/dogs/" + KNOWN_DOG_ID);
        page.waitForLoadState(LoadState.NETWORKIDLE);

        String sireText = page.locator("[data-testid='dog-card-sire']").textContent();
        String damText = page.locator("[data-testid='dog-card-dam']").textContent();

        assertTrue(sireText.contains(KNOWN_SIRE_NAME),
                "Sire section should mention '" + KNOWN_SIRE_NAME + "'; got: " + sireText);
        assertTrue(damText.contains(KNOWN_DAM_NAME),
                "Dam section should mention '" + KNOWN_DAM_NAME + "'; got: " + damText);
    }

    @Test
    @Order(5)
    @DisplayName("Pedigree link on dog card navigates to the pedigree page")
    void pedigreeLinkNavigatesToPedigreePage() {
        page.navigate(baseUrl + "/dogs/" + KNOWN_DOG_ID);
        page.waitForLoadState(LoadState.NETWORKIDLE);

        page.locator("[data-testid='pedigree-link']").click();
        page.waitForLoadState(LoadState.NETWORKIDLE);

        assertTrue(page.url().endsWith("/dogs/" + KNOWN_DOG_ID + "/pedigree"),
                "URL should be pedigree page; got: " + page.url());
    }

    // ------------------------------------------------------------------
    // Pedigree page
    // ------------------------------------------------------------------

    @Test
    @Order(6)
    @DisplayName("Pedigree page shows the correct root dog")
    void pedigreePageShowsRoot() {
        page.navigate(baseUrl + "/dogs/" + KNOWN_DOG_ID + "/pedigree");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        Locator root = page.locator("[data-testid='pedigree-root']");
        assertTrue(root.isVisible(), "pedigree-root must be visible");

        String rootText = root.textContent();
        assertTrue(rootText.contains(KNOWN_DOG_NAME),
                "Root should mention '" + KNOWN_DOG_NAME + "'; got: " + rootText);
        assertTrue(rootText.contains(String.valueOf(KNOWN_DOG_ID)),
                "Root should mention id " + KNOWN_DOG_ID + "; got: " + rootText);
    }

    @Test
    @Order(7)
    @DisplayName("Pedigree page lists both parents of dog 51 as ancestors")
    void pedigreePageShowsAncestors() {
        page.navigate(baseUrl + "/dogs/" + KNOWN_DOG_ID + "/pedigree");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        List<Locator> ancestorRows = page.locator("[data-testid='pedigree-ancestor']").all();
        assertFalse(ancestorRows.isEmpty(), "Ancestor rows should be present for dog 51");

        // Collect all ancestor dog-ids from data-dog-id attributes
        List<String> ancestorDogIds = ancestorRows.stream()
                .map(el -> el.getAttribute("data-dog-id"))
                .toList();

        assertTrue(ancestorDogIds.contains("1"), "Sire (id=1, Max) should be in ancestors");
        assertTrue(ancestorDogIds.contains("2"), "Dam (id=2, Lucy) should be in ancestors");
    }

    @Test
    @Order(8)
    @DisplayName("Pedigree page has no duplicate dog-ids across ancestor rows")
    void pedigreeAncestorRowsHaveNoDuplicateIds() {
        // Dog 452 (Louie) has a 6-generation chain; dedup is exercised under depth cap.
        page.navigate(baseUrl + "/dogs/452/pedigree");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        List<String> ids = page.locator("[data-testid='pedigree-ancestor']").all()
                .stream()
                .map(el -> el.getAttribute("data-dog-id"))
                .toList();

        long uniqueCount = ids.stream().distinct().count();
        assertEquals(uniqueCount, ids.size(),
                "Ancestor rows must not contain duplicate dog ids; found " + (ids.size() - uniqueCount) + " duplicates");
    }

    @Test
    @Order(9)
    @DisplayName("Pedigree page for a founder shows no ancestor rows")
    void founderDogHasNoAncestorRows() {
        // Dog 3 (Maggie) is a founder with no sire or dam.
        page.navigate(baseUrl + "/dogs/3/pedigree");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        List<Locator> ancestorRows = page.locator("[data-testid='pedigree-ancestor']").all();
        assertTrue(ancestorRows.isEmpty(), "Founder dog should have no ancestor rows");

        // "No ancestor records" fallback message should be shown
        Locator fallback = page.locator("[data-testid='pedigree-no-ancestors']");
        assertTrue(fallback.isVisible(), "No-ancestors fallback message must be visible");
    }

    @Test
    @Order(10)
    @DisplayName("Pedigree page for founder dog 3 shows descendants")
    void founderDogHasDescendants() {
        page.navigate(baseUrl + "/dogs/3/pedigree");
        page.waitForLoadState(LoadState.NETWORKIDLE);

        List<Locator> descendantRows = page.locator("[data-testid='pedigree-descendant']").all();
        assertTrue(descendantRows.size() > 0, "Maggie (dog 3) should have descendants in the UI");
    }

    // ------------------------------------------------------------------
    // Error handling
    // ------------------------------------------------------------------

    @Test
    @Order(11)
    @DisplayName("Navigating to a non-existent dog shows an error message, not a server crash")
    void nonExistentDogShowsErrorNotCrash() {
        page.navigate(baseUrl + "/dogs/" + NON_EXISTENT_DOG_ID);
        page.waitForLoadState(LoadState.NETWORKIDLE);

        // Page must not show a generic 500/traceback – an error element should be visible
        Locator errorEl = page.locator("[data-testid='error-message']");
        assertTrue(errorEl.isVisible(), "An error-message element must be shown for unknown dog");

        // No Python traceback should be visible (server-side unhandled exception)
        String pageText = page.textContent("body");
        assertFalse(pageText.contains("Traceback (most recent call last)"),
                "Python traceback must not be visible to the user");
    }
}
