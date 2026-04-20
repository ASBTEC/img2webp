/**
 * CONFIG — update these values
 */
const GH_OWNER = 'ASBTEC';
const GH_REPO = 'img2webp';
const GH_BRANCH = 'master';
const WORKFLOW_FILE = 'convertToWebp.yml'; // under .github/workflows/

const TARGET_FOLDER_ID = PropertiesService.getScriptProperties().getProperty('TARGET_FOLDER_ID');

/**
 * Trigger: From form → On form submit
 */
function onFormSubmit(e) {
  console.log(e)

  const formResponse = e.response;
  const answers = formResponse.getItemResponses();

  const email = answers[0].getResponse();        // first question = email
  const file_url = answers[1].getResponse()[0];  // second question = zip file
  const filename = DriveApp.getFileById(file_url).getName();

  console.log(email)
  console.log(file_url)
  console.log(filename)

  const pat = PropertiesService.getScriptProperties().getProperty('PROP_GITHUB_PAT');

  const url = `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;
  const payload = {
    ref: GH_BRANCH,
    inputs: { email, file_url, filename }
  };

  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    headers: {
      Authorization: `Bearer ${pat}`,
      Accept: 'application/vnd.github+json'
    },
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  Logger.log(response.getContentText());
}
