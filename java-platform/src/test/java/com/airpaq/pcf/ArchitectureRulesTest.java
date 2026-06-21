package com.airpaq.pcf;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

@AnalyzeClasses(packages = "com.airpaq.pcf", importOptions = ImportOption.DoNotIncludeTests.class)
class ArchitectureRulesTest {

    @ArchTest
    static final ArchRule controllersOnlyUseApplicationOrSharedContracts =
            noClasses()
                    .that()
                    .resideInAPackage("..api..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAnyPackage("..infrastructure..", "..persistence..");

    @ArchTest
    static final ArchRule applicationLayerDoesNotDependOnInfrastructure =
            noClasses()
                    .that()
                    .resideInAPackage("..application..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAnyPackage("..infrastructure..");

    @ArchTest
    static final ArchRule applicationLayerDoesNotUseJdbcDirectly =
            noClasses()
                    .that()
                    .resideInAPackage("..application..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAPackage("org.springframework.jdbc..");

    @ArchTest
    static final ArchRule sharedDoesNotDependOnBusinessModules =
            noClasses()
                    .that()
                    .resideInAPackage("com.airpaq.pcf.shared..")
                    .should()
                    .dependOnClassesThat()
                    .resideInAnyPackage(
                            "com.airpaq.pcf.catalog..",
                            "com.airpaq.pcf.imports..",
                            "com.airpaq.pcf.snapshots..",
                            "com.airpaq.pcf.calculations..",
                            "com.airpaq.pcf.approvals..",
                            "com.airpaq.pcf.exports..",
                            "com.airpaq.pcf.audit..",
                            "com.airpaq.pcf.health..");
}
