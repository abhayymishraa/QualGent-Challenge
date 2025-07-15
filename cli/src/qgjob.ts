#!/usr/bin/env node
import axios from "axios";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";

const API_URL = "http://localhost:8000";

yargs(hideBin(process.argv))
  .command(
    "submit",
    "Submit a new job to the QualGent server",
    (yargs) => {
      return yargs
        .option("org-id", {
          describe: "Organization ID",
          type: "string",
          demandOption: true,
        })
        .option("app-version-id", {
          describe: "Application Version ID",
          type: "string",
          demandOption: true,
        })
        .option("test", {
          describe: "Path to the test file",
          type: "string",
          demandOption: true,
        })
        .option("target", {
          describe: "Target device type",
          choices: ["emulator", "device", "browserstack"],
          demandOption: true,
        })
        .option("priority", {
          describe: "Job priority (1-10, 10 is highest)",
          type: "number",
          default: 5,
        })
        .option("max-retries", {
          describe: "Maximum number of retries on failure",
          type: "number",
          default: 3,
        });
    },
    async (argv) => {
      try {
        const payload = {
          org_id: argv.orgId,
          app_version_id: argv.appVersionId,
          test_path: argv.test,
          target: argv.target,
          priority: argv.priority,
          max_retries: argv.maxRetries,
        };
        const response = await axios.post(`${API_URL}/jobs`, payload);
        console.log("Job submitted successfully!");
        console.log(JSON.stringify(response.data, null, 2));
      } catch (err) {
        console.error("Error submitting job:");
        process.exitCode = 1;
      }
    }
  )
  .command(
    "status <job-id>",
    "Check the status of a job",
    (yargs) => {
      return yargs.positional("job-id", {
        describe: "The ID of the job to check",
        type: "string",
      });
    },
    async (argv) => {
      try {
        const response = await axios.get(`${API_URL}/jobs/${argv.jobId}`);
        console.log(`🔎 Status for job ${argv.jobId}:`);
        console.log(JSON.stringify(response.data, null, 2));
      } catch (err) {
        console.error("Error fetching job status:");
        process.exitCode = 1;
      }
    }
  )
  .demandCommand(1, "You must provide a valid command.")
  .help().argv;