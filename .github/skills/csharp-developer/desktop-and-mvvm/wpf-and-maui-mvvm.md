# Desktop & Client MVVM: WPF & .NET MAUI

Enterprise desktop and mobile client architectures using Model-View-ViewModel and `CommunityToolkit.Mvvm`.

---

## 1. MVVM Architecture Principles

```
  +------------------+         Data Binding / Commands        +----------------------+
  |       View       | <====================================> |      ViewModel       |
  | (XAML / Controls)|                                        | (State & Logic)      |
  +------------------+                                        +----------------------+
                                                                         |
                                                                         | Services & Repos
                                                                         v
                                                              +----------------------+
                                                              |        Model         |
                                                              | (Domain & Entities)  |
                                                              +----------------------+
```

- **View**: Declares UI markup (XAML). Purely visual; contains zero business logic.
- **ViewModel**: Exposes observable properties, formatted data, and UI commands (`ICommand`). Knows nothing of specific UI controls.
- **Model**: Domain entities, DTOs, and business rules.

---

## 2. Modern MVVM with `CommunityToolkit.Mvvm`

Replace hundreds of lines of boilerplate `INotifyPropertyChanged` and `ICommand` backing fields with source generators:

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

public partial class UserProfileViewModel : ObservableObject
{
    private readonly IUserService _userService;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(FullName))]
    [NotifyCanExecuteChangedFor(nameof(SaveProfileCommand))]
    private string _firstName = string.Empty;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(FullName))]
    [NotifyCanExecuteChangedFor(nameof(SaveProfileCommand))]
    private string _lastName = string.Empty;

    [ObservableProperty]
    private bool _isBusy;

    public string FullName => $"{FirstName} {LastName}".Trim();

    public UserProfileViewModel(IUserService userService)
    {
        _userService = userService;
    }

    private bool CanSave() => !IsBusy && !string.IsNullOrWhiteSpace(FirstName) && !string.IsNullOrWhiteSpace(LastName);

    [RelayCommand(CanExecute = nameof(CanSave))]
    private async Task SaveProfileAsync(CancellationToken cancellationToken)
    {
        IsBusy = true;
        try
        {
            await _userService.UpdateProfileAsync(FirstName, LastName, cancellationToken);
        }
        finally
        {
            IsBusy = false;
        }
    }
}
```

---

## 3. Decoupled Communication: `WeakReferenceMessenger`

Avoid strong reference memory leaks between ViewModels by passing messages via the `WeakReferenceMessenger`:

```csharp
// 1. Define message
public record UserLoggedInMessage(Guid UserId, string Username);

// 2. Sender ViewModel
public partial class LoginViewModel(IAuthService auth) : ObservableObject
{
    [RelayCommand]
    private async Task LoginAsync()
    {
        var user = await auth.AuthenticateAsync();
        WeakReferenceMessenger.Default.Send(new UserLoggedInMessage(user.Id, user.Username));
    }
}

// 3. Receiver ViewModel
public partial class DashboardViewModel : ObservableObject, IRecipient<UserLoggedInMessage>
{
    [ObservableProperty]
    private string _greeting = "Welcome!";

    public DashboardViewModel()
    {
        // Register this instance as recipient
        WeakReferenceMessenger.Default.Register<UserLoggedInMessage>(this);
    }

    public void Receive(UserLoggedInMessage message)
    {
        Greeting = $"Welcome back, {message.Username}!";
    }
}
```

---

## 4. UI Thread Marshaling & Async Dispatching

Updating bound UI properties from background threads or event callbacks will throw cross-thread exceptions (`InvalidOperationException: The calling thread cannot access this object because a different thread owns it`).

### WPF Thread Dispatching
```csharp
// WPF Dispatcher
Application.Current.Dispatcher.Invoke(() =>
{
    Items.Add(newItem);
});

// Or asynchronous dispatch
await Application.Current.Dispatcher.InvokeAsync(() =>
{
    Items.Add(newItem);
});
```

### .NET MAUI Thread Dispatching
```csharp
// .NET MAUI MainThread helper
MainThread.BeginInvokeOnMainThread(() =>
{
    Items.Add(newItem);
});
```

---

## 5. View-to-ViewModel Binding in XAML

Connect Views and ViewModels cleanly with Dependency Injection:

```xml
<UserControl x:Class="MyApp.Views.UserProfileView"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:d="http://schemas.microsoft.com/expression/blend/2008"
             xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
             xmlns:vm="clr-namespace:MyApp.ViewModels"
             d:DataContext="{d:DesignInstance Type=vm:UserProfileViewModel}">
    <StackPanel Margin="16" Spacing="8">
        <TextBox Text="{Binding FirstName, UpdateSourceTrigger=PropertyChanged}" />
        <TextBox Text="{Binding LastName, UpdateSourceTrigger=PropertyChanged}" />
        
        <TextBlock Text="{Binding FullName}" FontWeight="Bold" />
        
        <Button Content="Save" 
                Command="{Binding SaveProfileCommand}" />
                
        <ProgressBar IsIndeterminate="True" 
                     Visibility="{Binding IsBusy, Converter={StaticResource BooleanToVisibilityConverter}}" />
    </StackPanel>
</UserControl>
```
