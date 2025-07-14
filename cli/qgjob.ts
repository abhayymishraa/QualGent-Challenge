import axios from "axios";
import { argv } from "process";
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
        });
    },
    async (argv) => {
      try {
        const payload = {
          org_id: argv.orgId,
          app_version_id: argv.appVersionId,
          test_path: argv.test,
        };
        const response = await axios.post(`${API_URL}/jobs`, payload);
        console.log("Job submitted successfully");
        console.log(
          `Job ID: ${response.data.job_id}, Job Details: ${JSON.stringify(
            response.data
          )}`
        );
      } catch (err) {
        if (axios.isAxiosError(err)) {
          console.error("Error submitting job:", err.message);
        } else {
          console.error("An unknown error occurred:", err);
        }
      }
    }
  )

  .command(
    "status",
    "Check the status of a job",
    (yargs) => {
      return yargs.option("job-id", {
        describe: "The ID of the job to check",
        type: "string",
        demandOption: true,
      });
    },
    async (argv) => {
      try {
        const response = await axios.get(`${API_URL}/jobs/${argv.jobId}`);
        console.log(
          `Status for job ${response.data.job_id}: ${response.data.status}`
        );
        console.log(`Job Status: ${JSON.stringify(response.data)}`);
      } catch (err) {
        if (axios.isAxiosError(err)) {
          console.error("Error fetching job status:", err.message);
        } else {
          console.error("An unknown error occurred:", err);
        }
      }
    }
  )
  .demandCommand(1, "You must provide a valid command.")
  .help().argv;
