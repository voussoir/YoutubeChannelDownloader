const spinner = {};

/*
In general, spinners are used for functions that launch a callback, and the
callback will close the spinner after it runs. But, if your initial function
decides not to launch the callback (insufficient parameters, failed clientside
checks, etc.), you can have it return spinner.BAIL and the spinners will close
immediately. Of course, you're always welcome to use
window[button.dataset.spinnerCloser](), but this return value means you don't
need to pull the button into a variable, as long as you weren't using the
return value anyway.
*/
spinner.BAIL = "spinner.BAIL";

spinner.Spinner =
function Spinner(element)
{
    this.show = function(delay)
    {
        clearTimeout(this.delayed_showing_timeout);
        this.delayed_showing_timeout = null;

        if (delay)
        {
            this.delayed_showing_timeout = setTimeout(function(thisthis){thisthis.show()}, delay, this);
        }
        else
        {
            this.element.classList.remove("hidden");
        }
    }

    this.hide = function()
    {
        clearTimeout(this.delayed_showing_timeout);
        this.delayed_showing_timeout = null;

        this.element.classList.add("hidden");
    }

    this.delayed_showing_timeout = null;
    this.element = element;
}

spinner.spinner_button_index = 0;
spinner.button_spinner_groups = {};
/*
When a group member is closing, it will call the closer on all other members
in the group. Of course, this would recurse forever without some kind of
flagging, so this dict will hold group_id:true if a close is in progress,
and be empty otherwise.
*/
spinner.spinner_group_closing = {};

spinner.add_to_spinner_group =
function add_to_spinner_group(group_id, button)
{
    if (!(group_id in spinner.button_spinner_groups))
    {
        spinner.button_spinner_groups[group_id] = [];
    }
    spinner.button_spinner_groups[group_id].push(button);
}

spinner.close_grouped_spinners =
function close_grouped_spinners(group_id)
{
    if (group_id && !(spinner.spinner_group_closing[group_id]))
    {
        spinner.spinner_group_closing[group_id] = true;
        for (const button of spinner.button_spinner_groups[group_id])
        {
            window[button.dataset.spinnerCloser]();
        }
        delete spinner.spinner_group_closing[group_id];
    }
}

spinner.open_grouped_spinners =
function open_grouped_spinners(group_id)
{
    for (const button of spinner.button_spinner_groups[group_id])
    {
        window[button.dataset.spinnerOpener]();
    }
}

spinner.init_button_with_spinner =
function init_button_with_spinner()
{
    /*
    To create a button that has a spinner, and cannot be clicked again while
    the action is running, assign it the class "button_with_spinner".
    When you're ready for the spinner to disappear, call
    window[button.dataset.spinnerCloser]().

    Optional:
        data-spinner-id: If you want to use your own element as the spinner,
            give its ID here. Otherwise a new one will be created.

        data-spinner-delay: The number of milliseconds to wait before the
            spinner appears. For tasks that you expect to run very quickly,
            this helps prevent a pointlessly short spinner. Note that the button
            always becomes disabled immediately, and this delay only affects
            the separate spinner element.

        data-holder-class: CSS class for the new span that holds the menu.

        data-spinner-group: An opaque string. All button_with_spinner that have
            the same group will go into spinner mode when any of them is
            clicked. Useful if you want to have two copies of a button on the
            page, or two buttons which do opposite things and you only want one
            to run at a time.
    */
    const buttons = Array.from(document.getElementsByClassName("button_with_spinner"));
    for (const button of buttons)
    {
        button.classList.remove("button_with_spinner");
        button.innerHTML = button.innerHTML.trim();

        const holder = document.createElement("span");
        holder.classList.add("spinner_holder");
        holder.classList.add(button.dataset.holderClass || "spinner_holder");
        button.parentElement.insertBefore(holder, button);
        holder.appendChild(button);

        if (button.dataset.spinnerGroup)
        {
            spinner.add_to_spinner_group(button.dataset.spinnerGroup, button);
        }

        let spinner_element;
        if (button.dataset.spinnerId)
        {
            spinner_element = document.getElementById(button.dataset.spinnerId);
            spinner_element.classList.add("hidden");
        }
        else
        {
            spinner_element = document.createElement("span");
            spinner_element.innerText = "Working...";
            spinner_element.classList.add("hidden");
            holder.appendChild(spinner_element);
        }

        const spin = new spinner.Spinner(spinner_element);
        const spin_delay = parseFloat(button.dataset.spinnerDelay) || 0;

        button.dataset.spinnerOpener = "spinner_opener_" + spinner.spinner_button_index;
        window[button.dataset.spinnerOpener] = function spinner_opener()
        {
            spin.show(spin_delay);
            button.disabled = true;
        }
        // It is expected that the function referenced by onclick will call
        // window[button.dataset.spinnerCloser]() when appropriate, since from
        // our perspective we cannot be sure when to close the spinner.
        button.dataset.spinnerCloser = "spinner_closer_" + spinner.spinner_button_index;
        window[button.dataset.spinnerCloser] = function spinner_closer()
        {
            spinner.close_grouped_spinners(button.dataset.spinnerGroup);
            spin.hide();
            button.disabled = false;
        }

        const wrapped_onclick = button.onclick;
        button.removeAttribute('onclick');
        button.onclick = function()
        {
            if (button.dataset.spinnerGroup)
            {
                spinner.open_grouped_spinners(button.dataset.spinnerGroup);
            }
            else
            {
                window[button.dataset.spinnerOpener]();
            }
            const ret = wrapped_onclick();
            if (ret === spinner.BAIL)
            {
                window[button.dataset.spinnerCloser]();
            }
            return ret;
        }

        spinner.spinner_button_index += 1;
    }
}

spinner.on_pageload =
function on_pageload()
{
    spinner.init_button_with_spinner();
}
document.addEventListener("DOMContentLoaded", spinner.on_pageload);
