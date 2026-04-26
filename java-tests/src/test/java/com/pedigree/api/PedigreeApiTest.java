package com.pedigree.api;

import io.restassured.RestAssured;
import io.restassured.config.HttpClientConfig;
import io.restassured.config.RestAssuredConfig;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.*;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static io.restassured.RestAssured.given;
import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * API-level pedigree tests.
 *
 * Strategy:
 *   All tests run against a live instance of the Python app. The base URL
 *   defaults to http://127.0.0.1:8000 and is configurable via the
 *   {@code -Dbase.url=...} Maven property (or system property {@code base.url}).
 *
 *   Known facts drawn from Dogs Pedigree.csv used as golden values:
 *     - Dog 1  : Max, Labrador Retriever, Male – founder (no parents)
 *     - Dog 2  : Lucy, French Bulldog, Female – founder
 *     - Dog 3  : Maggie, Boxer, Male – founder, 119+ descendants within 5 gen
 *     - Dog 51 : Henry, sire_id=1, dam_id=2
 *     - Dog 452: Louie – ancestor chain reaches depth 6, so depth cap at 5 is exercised
 *
 * Assumption: the app is already running before this test class executes.
 */
@Tag("api")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class PedigreeApiTest {

    private static final int KNOWN_DOG_ID = 51;     // Henry: sire=1, dam=2
    private static final int FOUNDER_DOG_ID = 3;    // Maggie: many descendants, no parents
    private static final int DEEP_DOG_ID = 452;     // Louie: 6-level ancestor chain
    private static final int NON_EXISTENT_ID = 99999;
    private static final int MAX_GENERATIONS = 5;
    /** Local pedigree-network window (ancestors=2, descendants=2) must stay small. */
    private static final int PEDIGREE_NETWORK_WINDOW_MAX_NODES = 200;

    @BeforeAll
    static void configureRestAssured() {
        String baseUrl = System.getProperty("base.url", "http://127.0.0.1:8000");
        RestAssured.baseURI = baseUrl;
        RestAssured.config = RestAssuredConfig.config()
                .httpClient(HttpClientConfig.httpClientConfig()
                        .setParam("http.connection.timeout", 10_000)
                        .setParam("http.socket.timeout", 30_000));
    }

    private static void assertDogRecordHasRequiredFields(Map<String, Object> dog, String context) {
        assertTrue(dog.containsKey("id"), context + " missing field: id");
        assertTrue(dog.containsKey("name"), context + " missing field: name");
        assertTrue(dog.containsKey("breed"), context + " missing field: breed");
        assertTrue(dog.containsKey("sex"), context + " missing field: sex");
        assertTrue(dog.containsKey("height_cm"), context + " missing field: height_cm");
        assertTrue(dog.containsKey("weight_kg"), context + " missing field: weight_kg");
        assertTrue(dog.containsKey("sire_id"), context + " missing field: sire_id");
        assertTrue(dog.containsKey("dam_id"), context + " missing field: dam_id");
    }

    // ------------------------------------------------------------------
    // GET /api/dogs – list endpoint
    // ------------------------------------------------------------------

    @Test
    @Order(1)
    @DisplayName("GET /api/dogs returns 200 with a non-empty JSON array")
    void listDogsReturnsArray() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs")
        .then()
            .statusCode(200)
            .contentType(ContentType.JSON)
            .body("size()", greaterThan(500))   // baseline has 581 dogs
            .body("[0].id", notNullValue())
            .body("[0].name", not(emptyString()))
            .body("[0].breed", not(emptyString()))
            .body("[0].sex", not(emptyString()));
    }

    @Test
    @Order(2)
    @DisplayName("GET /api/dogs list: sampled rows + known id have all required fields")
    void listDogsContainsRequiredFields() {
        List<Map<String, Object>> dogs = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList(".");

        assertTrue(dogs.size() > 500, "expected full baseline dataset in list response");
        assertDogRecordHasRequiredFields(dogs.get(0), "list[0]");
        assertDogRecordHasRequiredFields(dogs.get(dogs.size() / 2), "list[mid]");
        assertDogRecordHasRequiredFields(dogs.get(dogs.size() - 1), "list[last]");

        Map<String, Object> dog51 = dogs.stream()
                .filter(d -> ((Number) d.get("id")).intValue() == KNOWN_DOG_ID)
                .findFirst()
                .orElse(null);
        assertNotNull(dog51, "known dog " + KNOWN_DOG_ID + " should appear in /api/dogs list");
        assertDogRecordHasRequiredFields(dog51, "list entry id=" + KNOWN_DOG_ID);
    }

    // ------------------------------------------------------------------
    // GET /api/dogs/{id} – detail endpoint
    // ------------------------------------------------------------------

    @Test
    @Order(3)
    @DisplayName("GET /api/dogs/3 returns founder Maggie with null parents from CSV")
    void getFounderDogByIdMatchesCsvData() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + FOUNDER_DOG_ID)
        .then()
            .statusCode(200)
            .body("id",      equalTo(FOUNDER_DOG_ID))
            .body("name",    equalTo("Maggie"))
            .body("breed",   equalTo("Boxer"))
            .body("sex",     equalTo("Male"))
            .body("sire_id", nullValue())
            .body("dam_id",  nullValue());
    }

    @Test
    @Order(4)
    @DisplayName("GET /api/dogs/51 returns Henry with correct parents from CSV")
    void getDogByIdMatchesCsvData() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + KNOWN_DOG_ID)
        .then()
            .statusCode(200)
            .body("id",      equalTo(KNOWN_DOG_ID))
            .body("name",    equalTo("Henry"))
            .body("sire_id", equalTo(1))
            .body("dam_id",  equalTo(2));
    }

    @Test
    @Order(5)
    @DisplayName("GET /api/dogs/{id} returns 404 with FastAPI detail for non-existent id")
    void getDogNotFoundReturns404() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + NON_EXISTENT_ID)
        .then()
            .statusCode(404)
            .contentType(ContentType.JSON)
            .body("detail", equalTo("Dog " + NON_EXISTENT_ID + " not found"));
    }

    // ------------------------------------------------------------------
    // GET /api/dogs/{id}/pedigree – pedigree endpoint
    // ------------------------------------------------------------------

    @Test
    @Order(6)
    @DisplayName("Pedigree response has required keys: root, ancestors, descendants")
    void pedigreeResponseShape() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + KNOWN_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .body("root",        notNullValue())
            .body("ancestors",   notNullValue())
            .body("descendants", notNullValue())
            .body("root.id",     equalTo(KNOWN_DOG_ID));
    }

    @Test
    @Order(7)
    @DisplayName("Pedigree ancestors of dog 51 include both parents (id=1 and id=2)")
    void pedigreeAncestorsContainBothParents() {
        List<Integer> ancestorIds = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + KNOWN_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("ancestors.id", Integer.class);

        assertTrue(ancestorIds.contains(1), "Ancestor list should contain sire id=1 (Max)");
        assertTrue(ancestorIds.contains(2), "Ancestor list should contain dam id=2 (Lucy)");
    }

    @Test
    @Order(8)
    @DisplayName("Pedigree ancestor depth is capped at MAX_GENERATIONS (" + MAX_GENERATIONS + ")")
    void pedigreeAncestorDepthIsCapped() {
        // Dog 452 has a 6-level ancestor chain; the API must cap it at 5.
        List<Integer> depths = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + DEEP_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("ancestors.depth", Integer.class);

        assertFalse(depths.isEmpty(), "Dog 452 should have ancestors");
        int maxDepth = depths.stream().mapToInt(Integer::intValue).max().orElse(0);
        assertTrue(maxDepth <= MAX_GENERATIONS,
                "Ancestor depth " + maxDepth + " exceeds cap of " + MAX_GENERATIONS);
    }

    @Test
    @Order(9)
    @DisplayName("Pedigree ancestor list contains no duplicate dog ids")
    void pedigreeAncestorsHaveNoDuplicateIds() {
        List<Integer> ancestorIds = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + DEEP_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("ancestors.id", Integer.class);

        Set<Integer> seen = new HashSet<>();
        List<Integer> duplicates = ancestorIds.stream()
                .filter(id -> !seen.add(id))
                .toList();
        assertTrue(duplicates.isEmpty(), "Duplicate ancestor ids: " + duplicates);
    }

    @Test
    @Order(10)
    @DisplayName("Pedigree descendant list contains no duplicate dog ids")
    void pedigreeDescendantsHaveNoDuplicateIds() {
        // Founder dog 3 (Maggie) has 119 descendants: a good dedup stress test.
        List<Integer> descendantIds = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + FOUNDER_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("descendants.id", Integer.class);

        assertFalse(descendantIds.isEmpty(), "Maggie (id=3) should have descendants");

        Set<Integer> seen = new HashSet<>();
        List<Integer> duplicates = descendantIds.stream()
                .filter(id -> !seen.add(id))
                .toList();
        assertTrue(duplicates.isEmpty(), "Duplicate descendant ids: " + duplicates);
    }

    @Test
    @Order(11)
    @DisplayName("Pedigree descendant depth is capped at MAX_GENERATIONS (" + MAX_GENERATIONS + ")")
    void pedigreeDescendantDepthIsCapped() {
        List<Integer> depths = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + FOUNDER_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("descendants.depth", Integer.class);

        int maxDepth = depths.stream().mapToInt(Integer::intValue).max().orElse(0);
        assertTrue(maxDepth <= MAX_GENERATIONS,
                "Descendant depth " + maxDepth + " exceeds cap of " + MAX_GENERATIONS);
    }

    @Test
    @Order(12)
    @DisplayName("GET /api/dogs/{id}/pedigree returns 404 with detail for non-existent dog")
    void pedigreeNotFoundReturns404() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + NON_EXISTENT_ID + "/pedigree")
        .then()
            .statusCode(404)
            .contentType(ContentType.JSON)
            .body("detail", equalTo("Dog " + NON_EXISTENT_ID + " not found"));
    }

    @Test
    @Order(13)
    @DisplayName("Pedigree of a founder dog has empty ancestors list")
    void founderDogHasNoAncestors() {
        // Dog 3 (Maggie) has no sire_id or dam_id in the CSV.
        List<?> ancestors = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + FOUNDER_DOG_ID + "/pedigree")
        .then()
            .statusCode(200)
            .extract().jsonPath().getList("ancestors");

        assertTrue(ancestors.isEmpty(), "Founder dog should have no ancestors; got " + ancestors.size());
    }

    @Test
    @Order(14)
    @DisplayName("GET /api/dogs/{id}/pedigree-network returns coherent local subgraph")
    void pedigreeNetworkLocalWindow() {
        Response res = given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/" + KNOWN_DOG_ID + "/pedigree-network?ancestors=2&descendants=2");

        res.then()
            .statusCode(200)
            .body("focus_id", equalTo(KNOWN_DOG_ID))
            .body("nodes", notNullValue())
            .body("edges", notNullValue())
            .body("nodes.size()", greaterThan(0))
            .body("nodes.size()", lessThanOrEqualTo(PEDIGREE_NETWORK_WINDOW_MAX_NODES));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> nodes = res.jsonPath().getList("nodes");
        Set<Integer> nodeIds = nodes.stream()
                .map(n -> ((Number) n.get("id")).intValue())
                .collect(Collectors.toSet());
        assertTrue(nodeIds.contains(KNOWN_DOG_ID), "focus dog must appear in nodes");

        for (Map<String, Object> n : nodes) {
            int gen = ((Number) n.get("generation")).intValue();
            assertTrue(gen >= -2 && gen <= 2,
                    "generation " + gen + " outside ±2 window");
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> edges = res.jsonPath().getList("edges");
        for (Map<String, Object> e : edges) {
            int parentId = ((Number) e.get("parent_id")).intValue();
            int childId = ((Number) e.get("child_id")).intValue();
            assertTrue(nodeIds.contains(parentId), "edge parent_id " + parentId + " not in nodes");
            assertTrue(nodeIds.contains(childId), "edge child_id " + childId + " not in nodes");
        }
    }

    @Test
    @Order(15)
    @DisplayName("GET /api/dogs with non-integer path id returns 422 (validation error)")
    void getDogWithInvalidPathIdReturns422() {
        given()
            .accept(ContentType.JSON)
        .when()
            .get("/api/dogs/not-a-number")
        .then()
            .statusCode(422)
            .contentType(ContentType.JSON)
            .body("detail", notNullValue());
    }
}
